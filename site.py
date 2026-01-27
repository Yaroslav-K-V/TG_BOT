import subprocess
import sys
import threading

from flask import Flask

app = Flask(__name__)


def run_bot() -> None:
    """Run the bot in a subprocess."""
    subprocess.Popen([sys.executable, "main_bot.py"])


@app.route('/')
def home():
    return "Bot is running!", 200


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    app.run(host="0.0.0.0", port=5000)
