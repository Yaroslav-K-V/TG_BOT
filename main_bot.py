import logging
from datetime import datetime, timedelta, date
from typing import Any

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import settings

settings.validate_config()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_TEXT = 0
WAITING_FOR_TIME = 1
WAITING_FOR_FREQUENCY = 2
WAITING_FOR_DELETE = 3

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
        "/list - View scheduled posts\n"
        "/delete - Delete a scheduled post\n"
        "/cancel - Cancel current operation"
    )


async def schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the scheduling process."""
    await check_daily_welcome(update, context)
    await update.message.reply_text(
        "Let's schedule a post!\n\n"
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
    user_id = update.effective_user.id

    job_name = f"post_{user_id}_{datetime.now().timestamp()}"
    post_time = datetime.strptime(time_str, "%H:%M").time()

    if frequency == 'daily':
        context.job_queue.run_daily(
            send_scheduled_post,
            time=post_time,
            data={'text': post_text, 'chat_id': settings.CHANNEL_ID, 'job_name': job_name},
            name=job_name,
        )
        freq_display = "Daily"
    else:
        now = datetime.now()
        target = now.replace(hour=post_time.hour, minute=post_time.minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        context.job_queue.run_once(
            send_scheduled_post_once,
            when=target,
            data={'text': post_text, 'chat_id': settings.CHANNEL_ID, 'job_name': job_name},
            name=job_name,
        )
        freq_display = "Once"

    scheduled_posts[job_name] = {
        'text': truncate(post_text, MAX_PREVIEW_LENGTH),
        'time': time_str,
        'user_id': user_id,
        'type': freq_display,
    }

    logger.info(f"Post scheduled by user {user_id}: [{time_str}, {freq_display}]")

    await update.message.reply_text(
        f"Post scheduled!\n\n"
        f"Time: {time_str} ({freq_display})\n"
        f"Text: {truncate(post_text, MAX_DISPLAY_LENGTH)}\n\n"
        f"The post will be sent to {settings.CHANNEL_ID}",
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
        message += f"{i}. [{data['time']} - {data['type']}] {data['text']}\n"

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
        message += f"{i}. [{data['time']} - {data['type']}] {data['text']}\n"
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
    application = Application.builder().token(settings.BOT_TOKEN).build()

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

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('list', list_posts))
    application.add_handler(schedule_handler)
    application.add_handler(delete_handler)

    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
