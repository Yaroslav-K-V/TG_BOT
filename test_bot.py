import logging
import asyncio
from telegram.ext import Application, CommandHandler

BOT_TOKEN = "6950127488:AAEhLvKr6OjfT7xf1DsCZaSCOr-x1phYa-c"
CHANNEL_ID = "@VirtuaCountryTropico"

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_command(update, context):
    """Функція для обробки команди /start"""
    await update.message.reply_text("Бот активний і готовий до роботи!")

async def help_command(update, context):
    """Функція для обробки команди /help"""
    await update.message.reply_text("Команди бота: /start, /help")

async def send_status(application):
    """Функція для періодичної перевірки і відправки повідомлень про активність бота"""
    while True:
        try:
            # Відправляємо повідомлення в канал кожні 5 хвилин
            await application.bot.send_message(chat_id=CHANNEL_ID, text="Бот активний!")
            logger.info("Повідомлення про активність відправлено.")
        except Exception as e:
            logger.error(f"Помилка при відправленні повідомлення: {e}")

        await asyncio.sleep(30)  # Чекаємо 5 хвилин (300 секунд)

async def main():
    # Створюємо Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Додаємо обробники команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    logger.info("Бот запущений і готовий до роботи!")

    # Ініціалізуємо бот
    await application.initialize()

    # Запускаємо паралельно функцію для періодичної перевірки активності
    asyncio.create_task(send_status(application))

    # Запускаємо бота в режимі довгого опитування
    await application.start()
    await application.updater.start_polling()

    # Блокуємо цикл подій, щоб бот працював постійно
    await application.updater.idle()

# Запускаємо бота через існуючий цикл подій
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (RuntimeError, KeyboardInterrupt) as e:
        logger.error(f"Зупинка бота через: {e}")
