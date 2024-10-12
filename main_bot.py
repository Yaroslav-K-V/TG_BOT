import logging
import requests
from telegram.ext import Application
import asyncio
import weather_posts
import settings  # Weather settings

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def send_message_via_api(message: str):
    """Send message through Telegram API."""
    BASE_URL = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": settings.CHANNEL_ID,
        "text": message
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        logging.info(f"Повідомлення відправлено: {message}")
    else:
        logging.error(f"Помилка відправки повідомлення: {response.text}")


async def post_weather():
    """Async function to post the weather."""
    post_text = weather_posts.post_weather_message()  # Викликаємо функцію, яка генерує текст повідомлення
    send_message_via_api(post_text)


async def schedule_posts():
    """Schedule regular weather posts."""
    import schedule
    schedule.every().day.at("00:00").do(lambda: asyncio.create_task(post_weather()))
    schedule.every().day.at("06:00").do(lambda: asyncio.create_task(post_weather()))
    schedule.every().day.at("09:00").do(lambda: asyncio.create_task(post_weather()))
    schedule.every().day.at("12:00").do(lambda: asyncio.create_task(post_weather()))
    schedule.every().day.at("15:00").do(lambda: asyncio.create_task(post_weather()))
    schedule.every().day.at("17:00").do(lambda: asyncio.create_task(post_weather()))
    schedule.every().day.at("20:00").do(lambda: asyncio.create_task(post_weather()))
    schedule.every().day.at("23:00").do(lambda: asyncio.create_task(post_weather()))
    
    """Test time"""
    schedule.every().day.at("20:37").do(lambda: asyncio.create_task(post_weather()))

    while True:
        schedule.run_pending()
        await asyncio.sleep(5)


async def main():
    application = Application.builder().token(settings.BOT_TOKEN).build()

    # Start the weather posting schedule
    await schedule_posts()

    # Run the bot
    await application.run_polling()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
