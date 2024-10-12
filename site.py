from flask import Flask
import threading
import subprocess

app = Flask(__name__)

# Запускаємо бота в окремому потоці
def run_bot():
    subprocess.Popen(["python", "main_bot.py"])

@app.route('/')
def home():
    return "Bot is running!", 200

if __name__ == "__main__":
    # Запускаємо бота в окремому потоці
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # Запускаємо Flask-сервер
    app.run(host="0.0.0.0", port=5000)
