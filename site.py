import threading
import time
from flask import Flask
import subprocess

app = Flask(__name__)

# Запускаємо основний бот у окремому потоці
def run_bot():
    subprocess.Popen(["python", "main_bot.py"])

@app.route('/')
def home():
    return "Bot is running!", 200

if __name__ == "__main__":
    # Запускаємо бота в окремому потоці, щоб він працював паралельно з вебсервером
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Запускаємо вебсервер
    app.run(host="0.0.0.0", port=5000)
