import logging
import requests
from urllib.parse import urlencode

# Налаштування
# Ваш токен потрібно помістити як рядок
BOT_TOKEN = "6950127488:AAEhLvKr6OjfT7xf1DsCZaSCOr-x1phYa-c"
CHANNEL_ID = "@VirtuaCountryTropico"

# Створюємо правильний URL
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def send_message_via_api(message: str):
    """Відправка повідомлення через Telegram API за допомогою HTTP-запиту."""
    try:
        # Закодуємо повідомлення для коректної передачі через URL
        encoded_message = urlencode({'text': message})

        # Формуємо URL для запиту
        full_url = f"{BASE_URL}?chat_id={CHANNEL_ID}&{encoded_message}"

        # Відправляємо запит
        response = requests.get(full_url)

        if response.status_code == 200:
            logger.info(f"Повідомлення відправлено: {message}")
        else:
            logger.error(f"Помилка при відправленні повідомлення: {response.text}")

    except Exception as e:
        logger.error(f"Помилка запиту: {e}")


def send_status():
    """Функція для перевірки і відправки повідомлення про активність кожні 5 хвилин."""
    try:
        message = "Бот активний!"
        send_message_via_api(message)
    except Exception as e:
        logger.error(f"Помилка: {e}")


if __name__ == '__main__':
    # Тестова відправка повідомлення через API
    send_message_via_api("Тестування API відправки повідомлень")
