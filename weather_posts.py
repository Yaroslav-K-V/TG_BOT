import settings
import random
from datetime import datetime
import pytz


def get_greeting():
    """Функція для отримання привітання на основі часу доби."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Доброго ранку, Великославія!"
    elif 12 <= current_hour < 18:
        return "Доброго дня, Великославія!"
    else:
        return "Доброго вечора, Великославія!"

def get_weather_emoji(condition: str) -> str:
    """Отримуємо емоджі для погодних умов."""
    emojis = {
        "sunny": "☀️",
        "cloudy": "☁️",
        "rainy": "🌧️",
        "snowy": "❄️",
        "windy": "💨",
        "stormy": "⛈️",
        "foggy": "🌫️",
        "clear": "🌙"
    }
    return emojis.get(condition, "")


def generate_weather(city, month):
    weather_data = settings.CITY_WEATHER_MAP.get(city, {}).get(month, None)

    if weather_data:
        temp_min, temp_max, condition = weather_data
        temp = random.randint(temp_min, temp_max)  # Генеруємо випадкову температуру в діапазоні
        emoji = settings.get_weather_emoji(condition)  # Додаємо емоджі до опису
        return f"{emoji} {condition}, {temp}°C"
    else:
        return "Немає даних"


def translate_weekday(weekday: str) -> str:
    """Переклад назв днів тижня з англійської на українську."""
    translation = {
        "Monday": "понеділок",
        "Tuesday": "вівторок",
        "Wednesday": "середа",
        "Thursday": "четвер",
        "Friday": "п'ятниця",
        "Saturday": "субота",
        "Sunday": "неділя"
    }
    return translation.get(weekday, weekday)




def post_weather_message():
    """Формування повідомлення про погоду для всіх міст."""
    timezone = pytz.timezone("Europe/Kyiv")
    now = datetime.now(timezone)
    month = now.month
    day = now.strftime("%d")
    weekday = translate_weekday(now.strftime("%A"))  # Використовуємо ручний переклад
    hour = now.strftime("%H:%M")

    # Отримання привітання
    greeting = get_greeting()

    # Словник для перекладу українських назв міст на англійські
    city_names_map = {
        "Бару": "Baru",
        "Марнар": "Marnar",
        "Капанія": "Kapaniya",
        "Баруль": "Barul",
        "Чернобай": "Chernobai",
        "Аркаль": "Arkal",
        "Ярон": "Yaron",
        "Гренден": "Grenden"
    }

    # Формуємо прогноз погоди
    cities = ["Бару", "Марнар", "Капанія", "Баруль", "Чернобай", "Аркаль", "Ярон", "Гренден"]
    forecast = "\n\n".join([f"{city}: {generate_weather(city_names_map[city], month)}" for city in cities])

    # Формуємо текст повідомлення
    post_text = (f"{greeting} Сьогодні {weekday}, {day} число, і наступає час прогнозу погоди на {hour}:\n\n"
                 f"{forecast}")

    return post_text


