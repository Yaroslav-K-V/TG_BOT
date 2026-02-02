import logging
import re
from datetime import datetime, timedelta, date, timezone
from typing import Any
from zoneinfo import ZoneInfo

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
    Defaults,
)

import settings

settings.validate_config()


class TokenFilter(logging.Filter):
    """Filter to mask bot tokens in log messages."""
    TOKEN_PATTERN = re.compile(r'bot\d+:[A-Za-z0-9_-]+')

    def filter(self, record: logging.LogRecord) -> bool:
        # Mask in message
        if record.msg:
            record.msg = self.TOKEN_PATTERN.sub('bot***:***', str(record.msg))
        # Mask in args (httpx uses this)
        if record.args:
            record.args = tuple(
                self.TOKEN_PATTERN.sub('bot***:***', str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO)
)

# Mask tokens in all loggers (especially httpx)
for handler in logging.root.handlers:
    handler.addFilter(TokenFilter())

# Reduce httpx verbosity (optional: change to WARNING to hide all HTTP logs)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Enable apscheduler debug logging
logging.getLogger("apscheduler").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_TEXT = 0
WAITING_FOR_TIME = 1
WAITING_FOR_FREQUENCY = 2
WAITING_FOR_DELETE = 3
WAITING_FOR_EDIT_SELECT = 4
WAITING_FOR_EDIT_CHOICE = 5
WAITING_FOR_EDIT_TEXT = 6
WAITING_FOR_EDIT_TIME = 7
WAITING_FOR_BATCH_TEXT = 8
WAITING_FOR_BATCH_TIME = 9
WAITING_FOR_BATCH_FREQUENCY = 10

# Timezone
TZ = ZoneInfo("Europe/Kyiv")

# Display limits
MAX_PREVIEW_LENGTH = 50
MAX_DISPLAY_LENGTH = 100
MAX_POST_LENGTH = 4096

scheduled_posts: dict[str, dict[str, Any]] = {}
user_last_interaction: dict[int, date] = {}


def get_daily_greeting() -> str:
    """Get greeting based on time of day."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 18:
        return "Good afternoon"
    else:
        return "Good evening"


def truncate(text: str, length: int) -> str:
    """Truncate text to given length with ellipsis."""
    return text[:length] + '...' if len(text) > length else text


def count_user_posts(user_id: int) -> int:
    """Count scheduled posts for a user."""
    return sum(1 for data in scheduled_posts.values() if data['user_id'] == user_id)


async def check_daily_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user should receive daily welcome. Returns True if welcome was sent."""
    if not update.effective_user or not update.message:
        return False

    user_id = update.effective_user.id
    user_name = update.effective_user.username or update.effective_user.first_name or "there"
    today = date.today()

    last_date = user_last_interaction.get(user_id)
    user_last_interaction[user_id] = today

    if last_date != today:
        greeting = get_daily_greeting()
        await update.message.reply_text(
            f"{greeting}, {user_name}! Welcome back!\n\n"
            f"You have {count_user_posts(user_id)} scheduled post(s).\n"
            f"Use /schedule to create a new one."
        )
        return True
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message."""
    await check_daily_welcome(update, context)
    await update.message.reply_text(
        "I can schedule posts for you.\n\n"
        "Commands:\n"
        "/schedule - Schedule a new post\n"
        "/batch - Schedule multiple posts at once\n"
        "/list - View scheduled posts\n"
        "/edit - Edit a scheduled post\n"
        "/delete - Delete a scheduled post\n"
        "/cancel - Cancel current operation"
    )


def get_target_chat(update: Update) -> tuple[int | str, str]:
    """Get the target chat for posting. Returns (chat_id, display_name)."""
    chat = update.effective_chat
    if chat.type in ("group", "supergroup"):
        return chat.id, chat.title or str(chat.id)
    return settings.CHANNEL_ID, str(settings.CHANNEL_ID)


async def schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the scheduling process."""
    await check_daily_welcome(update, context)

    chat_id, chat_name = get_target_chat(update)
    context.user_data['target_chat_id'] = chat_id
    context.user_data['target_chat_name'] = chat_name

    await update.message.reply_text(
        f"Let's schedule a post for {chat_name}!\n\n"
        "Please enter the text you want to post:"
    )
    return WAITING_FOR_TEXT


async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the post text and ask for time."""
    text = update.message.text.strip()

    if not text:
        await update.message.reply_text("Text cannot be empty. Please enter the post text:")
        return WAITING_FOR_TEXT

    if len(text) > MAX_POST_LENGTH:
        await update.message.reply_text(
            f"Text is too long ({len(text)} chars). "
            f"Telegram limit is {MAX_POST_LENGTH} characters. Please shorten it:"
        )
        return WAITING_FOR_TEXT

    context.user_data['post_text'] = text
    await update.message.reply_text(
        "Got it! Now enter the time to post.\n\n"
        "Format: HH:MM (24-hour format)\n"
        "Example: 14:30"
    )
    return WAITING_FOR_TIME


async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the time and ask for frequency."""
    time_str = update.message.text.strip()

    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError()
    except (ValueError, AttributeError):
        await update.message.reply_text(
            "Invalid time format. Please use HH:MM (e.g., 14:30)"
        )
        return WAITING_FOR_TIME

    context.user_data['post_time'] = time_str

    keyboard = [["Once", "Daily"]]
    await update.message.reply_text(
        "How often should this post be sent?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return WAITING_FOR_FREQUENCY


async def receive_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive frequency and schedule the post."""
    frequency = update.message.text.strip().lower()

    if frequency not in ['once', 'daily']:
        keyboard = [["Once", "Daily"]]
        await update.message.reply_text(
            "Please choose 'Once' or 'Daily'",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return WAITING_FOR_FREQUENCY

    post_text = context.user_data.get('post_text', '')
    time_str = context.user_data.get('post_time', '')
    target_chat_id = context.user_data.get('target_chat_id', settings.CHANNEL_ID)
    target_chat_name = context.user_data.get('target_chat_name', str(settings.CHANNEL_ID))
    user_id = update.effective_user.id

    job_name = f"post_{user_id}_{datetime.now().timestamp()}"
    post_time = datetime.strptime(time_str, "%H:%M").time()
    job_data = {'text': post_text, 'chat_id': target_chat_id, 'job_name': job_name}

    if frequency == 'daily':
        context.job_queue.run_daily(
            send_scheduled_post,
            time=post_time,
            data=job_data,
            name=job_name,
        )
        freq_display = "Daily"
    else:
        now = datetime.now(TZ)
        target = now.replace(hour=post_time.hour, minute=post_time.minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        logger.info(f"DEBUG: now={now}, target={target}, diff={(target-now).total_seconds()}s")

        context.job_queue.run_once(
            send_scheduled_post_once,
            when=target,
            data=job_data,
            name=job_name,
        )
        freq_display = "Once"

    scheduled_posts[job_name] = {
        'text': truncate(post_text, MAX_PREVIEW_LENGTH),
        'full_text': post_text,
        'time': time_str,
        'user_id': user_id,
        'type': freq_display,
        'target': target_chat_name,
        'chat_id': target_chat_id,
    }

    logger.info(f"Post scheduled by user {user_id}: [{time_str}, {freq_display}] -> {target_chat_name}")

    await update.message.reply_text(
        f"Post scheduled!\n\n"
        f"Time: {time_str} ({freq_display})\n"
        f"Text: {truncate(post_text, MAX_DISPLAY_LENGTH)}\n\n"
        f"The post will be sent to {target_chat_name}",
        reply_markup=ReplyKeyboardRemove()
    )

    context.user_data.clear()
    return ConversationHandler.END


async def send_scheduled_post(context: ContextTypes.DEFAULT_TYPE):
    """Send the scheduled post to the channel (daily)."""
    job_data = context.job.data
    try:
        await context.bot.send_message(
            chat_id=job_data['chat_id'],
            text=job_data['text']
        )
        logger.info(f"Scheduled post sent: {job_data['text'][:50]}...")
    except TelegramError as e:
        logger.error(f"Telegram error sending post: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending post: {e}")


async def send_scheduled_post_once(context: ContextTypes.DEFAULT_TYPE):
    """Send the scheduled post to the channel (once) and remove from list."""
    logger.info("DEBUG: send_scheduled_post_once called!")
    job_data = context.job.data
    try:
        await context.bot.send_message(
            chat_id=job_data['chat_id'],
            text=job_data['text']
        )
        logger.info(f"One-time post sent: {job_data['text'][:50]}...")
        job_name = job_data.get('job_name')
        if job_name and job_name in scheduled_posts:
            del scheduled_posts[job_name]
    except TelegramError as e:
        logger.error(f"Telegram error sending one-time post: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending one-time post: {e}")


async def list_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all scheduled posts."""
    await check_daily_welcome(update, context)

    user_id = update.effective_user.id

    user_posts = [
        (name, data) for name, data in scheduled_posts.items()
        if data['user_id'] == user_id
    ]

    if not user_posts:
        await update.message.reply_text("You have no scheduled posts.")
        return

    message = "Your scheduled posts:\n\n"
    for i, (name, data) in enumerate(user_posts, 1):
        target = data.get('target', settings.CHANNEL_ID)
        message += f"{i}. [{data['time']} - {data['type']}] ({target}) {data['text']}\n"

    await update.message.reply_text(message)


async def delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the delete process."""
    await check_daily_welcome(update, context)

    user_id = update.effective_user.id

    user_posts = [
        (name, data) for name, data in scheduled_posts.items()
        if data['user_id'] == user_id
    ]

    if not user_posts:
        await update.message.reply_text("You have no scheduled posts to delete.")
        return ConversationHandler.END

    context.user_data['user_posts'] = user_posts

    message = "Which post do you want to delete?\n\n"
    for i, (name, data) in enumerate(user_posts, 1):
        target = data.get('target', settings.CHANNEL_ID)
        message += f"{i}. [{data['time']} - {data['type']}] ({target}) {data['text']}\n"
    message += "\nEnter the number to delete (or /cancel):"

    await update.message.reply_text(message)
    return WAITING_FOR_DELETE


async def receive_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete the selected post."""
    user_posts = context.user_data.get('user_posts', [])

    try:
        num = int(update.message.text.strip())
        if num < 1 or num > len(user_posts):
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            f"Please enter a number between 1 and {len(user_posts)}"
        )
        return WAITING_FOR_DELETE

    job_name, data = user_posts[num - 1]

    jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in jobs:
        job.schedule_removal()

    if job_name in scheduled_posts:
        del scheduled_posts[job_name]

    logger.info(f"Post deleted by user {update.effective_user.id}: {job_name}")

    await update.message.reply_text(
        f"Deleted post #{num}: [{data['time']}] {data['text']}"
    )

    context.user_data.clear()
    return ConversationHandler.END


# ============ EDIT COMMAND ============

async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the edit process."""
    await check_daily_welcome(update, context)

    user_id = update.effective_user.id

    user_posts = [
        (name, data) for name, data in scheduled_posts.items()
        if data['user_id'] == user_id
    ]

    if not user_posts:
        await update.message.reply_text("You have no scheduled posts to edit.")
        return ConversationHandler.END

    context.user_data['user_posts'] = user_posts

    message = "Which post do you want to edit?\n\n"
    for i, (name, data) in enumerate(user_posts, 1):
        target = data.get('target', settings.CHANNEL_ID)
        message += f"{i}. [{data['time']} - {data['type']}] ({target}) {data['text']}\n"
    message += "\nEnter the number to edit (or /cancel):"

    await update.message.reply_text(message)
    return WAITING_FOR_EDIT_SELECT


async def receive_edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive which post to edit."""
    user_posts = context.user_data.get('user_posts', [])

    try:
        num = int(update.message.text.strip())
        if num < 1 or num > len(user_posts):
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            f"Please enter a number between 1 and {len(user_posts)}"
        )
        return WAITING_FOR_EDIT_SELECT

    job_name, data = user_posts[num - 1]
    context.user_data['edit_job_name'] = job_name
    context.user_data['edit_data'] = data

    keyboard = [["Text", "Time"]]
    await update.message.reply_text(
        f"Editing post #{num}: [{data['time']}] {data['text']}\n\n"
        "What do you want to change?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return WAITING_FOR_EDIT_CHOICE


async def receive_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive what to edit (text or time)."""
    choice = update.message.text.strip().lower()

    if choice == 'text':
        data = context.user_data.get('edit_data', {})
        full_text = data.get('full_text', data.get('text', ''))
        await update.message.reply_text(
            f"Current text:\n{full_text}\n\nEnter the new text:",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_FOR_EDIT_TEXT
    elif choice == 'time':
        data = context.user_data.get('edit_data', {})
        await update.message.reply_text(
            f"Current time: {data.get('time', 'N/A')}\n\n"
            "Enter the new time (HH:MM format):",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_FOR_EDIT_TIME
    else:
        keyboard = [["Text", "Time"]]
        await update.message.reply_text(
            "Please choose 'Text' or 'Time'",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return WAITING_FOR_EDIT_CHOICE


async def receive_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive new text for the post."""
    new_text = update.message.text.strip()

    if not new_text:
        await update.message.reply_text("Text cannot be empty. Please enter the new text:")
        return WAITING_FOR_EDIT_TEXT

    if len(new_text) > MAX_POST_LENGTH:
        await update.message.reply_text(
            f"Text is too long ({len(new_text)} chars). "
            f"Telegram limit is {MAX_POST_LENGTH} characters. Please shorten it:"
        )
        return WAITING_FOR_EDIT_TEXT

    job_name = context.user_data.get('edit_job_name')
    data = context.user_data.get('edit_data', {})

    # Update job data
    jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in jobs:
        job.data['text'] = new_text

    # Update scheduled_posts
    if job_name in scheduled_posts:
        scheduled_posts[job_name]['text'] = truncate(new_text, MAX_PREVIEW_LENGTH)
        scheduled_posts[job_name]['full_text'] = new_text

    logger.info(f"Post edited by user {update.effective_user.id}: {job_name} - text updated")

    await update.message.reply_text(
        f"Post updated!\n\n"
        f"New text: {truncate(new_text, MAX_DISPLAY_LENGTH)}"
    )

    context.user_data.clear()
    return ConversationHandler.END


async def receive_edit_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive new time for the post."""
    time_str = update.message.text.strip()

    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError()
    except (ValueError, AttributeError):
        await update.message.reply_text(
            "Invalid time format. Please use HH:MM (e.g., 14:30)"
        )
        return WAITING_FOR_EDIT_TIME

    job_name = context.user_data.get('edit_job_name')
    data = context.user_data.get('edit_data', {})
    user_id = update.effective_user.id

    # Remove old job
    jobs = context.job_queue.get_jobs_by_name(job_name)
    old_job_data = None
    for job in jobs:
        old_job_data = job.data
        job.schedule_removal()

    if not old_job_data:
        await update.message.reply_text("Error: Could not find the scheduled job.")
        context.user_data.clear()
        return ConversationHandler.END

    # Create new job with updated time
    post_time = datetime.strptime(time_str, "%H:%M").time()
    post_type = data.get('type', 'Once')

    if post_type == 'Daily':
        context.job_queue.run_daily(
            send_scheduled_post,
            time=post_time,
            data=old_job_data,
            name=job_name,
        )
    else:
        now = datetime.now(TZ)
        target = now.replace(hour=post_time.hour, minute=post_time.minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        context.job_queue.run_once(
            send_scheduled_post_once,
            when=target,
            data=old_job_data,
            name=job_name,
        )

    # Update scheduled_posts
    if job_name in scheduled_posts:
        scheduled_posts[job_name]['time'] = time_str

    logger.info(f"Post edited by user {user_id}: {job_name} - time updated to {time_str}")

    await update.message.reply_text(
        f"Post updated!\n\n"
        f"New time: {time_str}"
    )

    context.user_data.clear()
    return ConversationHandler.END


# ============ BATCH SCHEDULING ============

async def batch_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start batch scheduling process."""
    await check_daily_welcome(update, context)

    chat_id, chat_name = get_target_chat(update)
    context.user_data['target_chat_id'] = chat_id
    context.user_data['target_chat_name'] = chat_name

    await update.message.reply_text(
        f"Batch scheduling for {chat_name}!\n\n"
        "Enter multiple posts, each on a new line.\n"
        "Separate posts with '---' on its own line.\n\n"
        "Example:\n"
        "First post text\n"
        "---\n"
        "Second post text\n"
        "---\n"
        "Third post text"
    )
    return WAITING_FOR_BATCH_TEXT


async def receive_batch_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive batch posts text."""
    raw_text = update.message.text.strip()

    # Split by --- delimiter
    posts = [p.strip() for p in raw_text.split('---') if p.strip()]

    if not posts:
        await update.message.reply_text(
            "No posts found. Please enter posts separated by '---':"
        )
        return WAITING_FOR_BATCH_TEXT

    # Validate each post
    for i, post in enumerate(posts, 1):
        if len(post) > MAX_POST_LENGTH:
            await update.message.reply_text(
                f"Post #{i} is too long ({len(post)} chars). "
                f"Telegram limit is {MAX_POST_LENGTH} characters. Please re-enter all posts:"
            )
            return WAITING_FOR_BATCH_TEXT

    context.user_data['batch_posts'] = posts
    await update.message.reply_text(
        f"Got {len(posts)} post(s)!\n\n"
        "Now enter the time to post all of them.\n"
        "Format: HH:MM (24-hour format)\n"
        "Example: 14:30"
    )
    return WAITING_FOR_BATCH_TIME


async def receive_batch_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive time for batch posts."""
    time_str = update.message.text.strip()

    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError()
    except (ValueError, AttributeError):
        await update.message.reply_text(
            "Invalid time format. Please use HH:MM (e.g., 14:30)"
        )
        return WAITING_FOR_BATCH_TIME

    context.user_data['batch_time'] = time_str

    keyboard = [["Once", "Daily"]]
    await update.message.reply_text(
        "How often should these posts be sent?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return WAITING_FOR_BATCH_FREQUENCY


async def receive_batch_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive frequency and schedule all batch posts."""
    frequency = update.message.text.strip().lower()

    if frequency not in ['once', 'daily']:
        keyboard = [["Once", "Daily"]]
        await update.message.reply_text(
            "Please choose 'Once' or 'Daily'",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return WAITING_FOR_BATCH_FREQUENCY

    posts = context.user_data.get('batch_posts', [])
    time_str = context.user_data.get('batch_time', '')
    target_chat_id = context.user_data.get('target_chat_id', settings.CHANNEL_ID)
    target_chat_name = context.user_data.get('target_chat_name', str(settings.CHANNEL_ID))
    user_id = update.effective_user.id

    post_time = datetime.strptime(time_str, "%H:%M").time()
    freq_display = "Daily" if frequency == 'daily' else "Once"
    scheduled_count = 0

    for i, post_text in enumerate(posts):
        job_name = f"post_{user_id}_{datetime.now().timestamp()}_{i}"
        job_data = {'text': post_text, 'chat_id': target_chat_id, 'job_name': job_name}

        if frequency == 'daily':
            context.job_queue.run_daily(
                send_scheduled_post,
                time=post_time,
                data=job_data,
                name=job_name,
            )
        else:
            now = datetime.now(TZ)
            target = now.replace(hour=post_time.hour, minute=post_time.minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)

            context.job_queue.run_once(
                send_scheduled_post_once,
                when=target,
                data=job_data,
                name=job_name,
            )

        scheduled_posts[job_name] = {
            'text': truncate(post_text, MAX_PREVIEW_LENGTH),
            'full_text': post_text,
            'time': time_str,
            'user_id': user_id,
            'type': freq_display,
            'target': target_chat_name,
            'chat_id': target_chat_id,
        }
        scheduled_count += 1

    logger.info(f"Batch scheduled by user {user_id}: {scheduled_count} posts at {time_str} ({freq_display})")

    await update.message.reply_text(
        f"Batch scheduled!\n\n"
        f"Posts: {scheduled_count}\n"
        f"Time: {time_str} ({freq_display})\n"
        f"Target: {target_chat_name}",
        reply_markup=ReplyKeyboardRemove()
    )

    context.user_data.clear()
    return ConversationHandler.END


# ============ ADMIN DASHBOARD ============

async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin dashboard with stats."""
    user_id = update.effective_user.id

    # Check if user is admin
    if settings.ADMIN_ID and str(user_id) != str(settings.ADMIN_ID):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    total_posts = len(scheduled_posts)
    daily_posts = sum(1 for d in scheduled_posts.values() if d['type'] == 'Daily')
    once_posts = sum(1 for d in scheduled_posts.values() if d['type'] == 'Once')

    # Count posts by user
    user_counts: dict[int, int] = {}
    for data in scheduled_posts.values():
        uid = data['user_id']
        user_counts[uid] = user_counts.get(uid, 0) + 1

    # Count posts by target
    target_counts: dict[str, int] = {}
    for data in scheduled_posts.values():
        target = data.get('target', 'Unknown')
        target_counts[target] = target_counts.get(target, 0) + 1

    message = "📊 Admin Dashboard\n\n"
    message += f"Total scheduled posts: {total_posts}\n"
    message += f"├ Daily: {daily_posts}\n"
    message += f"└ One-time: {once_posts}\n\n"

    if user_counts:
        message += f"Posts by user ({len(user_counts)} users):\n"
        for uid, count in sorted(user_counts.items(), key=lambda x: -x[1])[:10]:
            message += f"├ User {uid}: {count} post(s)\n"
        message += "\n"

    if target_counts:
        message += f"Posts by target ({len(target_counts)} targets):\n"
        for target, count in sorted(target_counts.items(), key=lambda x: -x[1])[:10]:
            message += f"├ {target}: {count} post(s)\n"
        message += "\n"

    message += f"Active users today: {len(user_last_interaction)}"

    await update.message.reply_text(message)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current operation."""
    context.user_data.clear()
    await update.message.reply_text(
        "Operation cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main():
    """Run the bot."""
    # Use Kyiv timezone for scheduling
    defaults = Defaults(tzinfo=ZoneInfo("Europe/Kyiv"))
    application = Application.builder().token(settings.BOT_TOKEN).defaults(defaults).build()

    schedule_handler = ConversationHandler(
        entry_points=[CommandHandler('schedule', schedule_start)],
        states={
            WAITING_FOR_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)
            ],
            WAITING_FOR_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time)
            ],
            WAITING_FOR_FREQUENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_frequency)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    delete_handler = ConversationHandler(
        entry_points=[CommandHandler('delete', delete_start)],
        states={
            WAITING_FOR_DELETE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delete)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    edit_handler = ConversationHandler(
        entry_points=[CommandHandler('edit', edit_start)],
        states={
            WAITING_FOR_EDIT_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_select)
            ],
            WAITING_FOR_EDIT_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_choice)
            ],
            WAITING_FOR_EDIT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_text)
            ],
            WAITING_FOR_EDIT_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_time)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    batch_handler = ConversationHandler(
        entry_points=[CommandHandler('batch', batch_start)],
        states={
            WAITING_FOR_BATCH_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_batch_text)
            ],
            WAITING_FOR_BATCH_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_batch_time)
            ],
            WAITING_FOR_BATCH_FREQUENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_batch_frequency)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('list', list_posts))
    application.add_handler(CommandHandler('admin', admin_dashboard))
    application.add_handler(schedule_handler)
    application.add_handler(delete_handler)
    application.add_handler(edit_handler)
    application.add_handler(batch_handler)

    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
