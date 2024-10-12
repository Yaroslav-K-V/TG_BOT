from flask import Flask
import threading
import subprocess

app = Flask(__name__)

# Запуск main_bot.py у фоновому режимі
def start_bot():
    subprocess.Popen(['python', 'main_bot.py'])

# Роут для пінгу
@app.route('/')
def ping():
    return "Bot is running!"

if __name__ == "__main__":
    # Запускаємо бота в окремому потоці
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.start()

    # Запускаємо Flask сервер
    app.run(host="0.0.0.0", port=5000)

