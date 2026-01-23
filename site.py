import subprocess
import threading

from flask import Flask

app = Flask(__name__)


def run_bot():
    """Run the bot in a subprocess."""
    subprocess.Popen(["python", "main_bot.py"])


@app.route('/')
def home():
    return "Bot is running!", 200


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host="0.0.0.0", port=5000)
