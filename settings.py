import random

CHANNEL_ID = "@VirtuaCountryTropico"

# Погодні дані для Бару
BARU_WEATHER = {
    1: (5, 10, "Дощова і вітряна погода"),
    2: (8, 12, "Хмарно"),
    3: (10, 15, "Переважно сонячно"),
    4: (15, 20, "Тепло"),
    5: (20, 25, "Сонячно"),
    6: (25, 30, "Жарко"),
    7: (27, 32, "Спекотно"),
    8: (30, 35, "Спекотно і сухо"),
    9: (20, 25, "Тепло"),
    10: (15, 20, "Прохолодно"),
    11: (10, 15, "Хмарно"),
    12: (5, 10, "Дощова і холодна погода"),
}

# Погодні дані для Марнара
MARNAR_WEATHER = {
    1: (-2, 2, "Холодно"),
    2: (-1, 3, "Морозно"),
    3: (4, 8, "Тепліше"),
    4: (10, 15, "Весняна погода"),
    5: (20, 25, "Тепло"),
    6: (25, 30, "Жарко"),
    7: (30, 35, "Спекотно"),
    8: (33, 38, "Спекотно і сухо"),
    9: (20, 25, "Тепло"),
    10: (12, 17, "Прохолодно"),
    11: (8, 12, "Осінь"),
    12: (-3, 2, "Холодно і сніжно"),
}

# Подібні дані для інших міст (Капанія, Баруль, Чернобай, Аркаль, Ярон, Гренден)
KAPANIYA_WEATHER = BARU_WEATHER
BARUL_WEATHER = MARNAR_WEATHER
CHERNOBAI_WEATHER = BARU_WEATHER
ARKAL_WEATHER = MARNAR_WEATHER
YARON_WEATHER = BARU_WEATHER
GRENDEN_WEATHER = MARNAR_WEATHER

# Мапа для міста і відповідного погодного словника
CITY_WEATHER_MAP = {
    "Baru": BARU_WEATHER,
    "Marnar": MARNAR_WEATHER,
    "Kapaniya": KAPANIYA_WEATHER,
    "Barul": BARUL_WEATHER,
    "Chernobai": CHERNOBAI_WEATHER,
    "Arkal": ARKAL_WEATHER,
    "Yaron": YARON_WEATHER,
    "Grenden": GRENDEN_WEATHER,
}


def get_weather_emoji(description: str) -> str:
    """
    Повертає емоджі на основі опису погоди.
    """
    if "сонячно" in description.lower():
        return "☀️"
    elif "хмарно" in description.lower():
        return "☁️"
    elif "дощ" in description.lower():
        return "🌧️"
    elif "спекотно" in description.lower():
        return "🔥"
    elif "холодно" in description.lower():
        return "❄️"
    elif "вітряна" in description.lower():
        return "💨"
    else:
        return "🌤️"

