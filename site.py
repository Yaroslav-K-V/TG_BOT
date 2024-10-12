from flask import Flask
import threading
import time
import telebot  # ваш телеграм бот

app = Flask(__name__)

# Запуск бота у фоновому режимі
def start_bot():
    bot = telebot.TeleBot("YOUR_TOKEN_HERE")
    # ваш код бота
    bot.infinity_polling()

# Роут для пінгу
@app.route('/')
def ping():
    return "Bot is running"

if __name__ == "__main__":
    # Запускаємо бота в окремому потоці
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.start()

    # Запускаємо Flask сервер
    app.run(host="0.0.0.0", port=5000)
