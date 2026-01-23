# Telegram Post Scheduler Bot

A Telegram bot that allows users to schedule posts to a channel.

## Features

- Schedule posts for one-time or daily delivery
- View and manage scheduled posts
- Daily welcome message on first interaction
- Simple conversation-based interface

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and help |
| `/schedule` | Schedule a new post |
| `/list` | View your scheduled posts |
| `/delete` | Delete a scheduled post |
| `/cancel` | Cancel current operation |

## Setup

### 1. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy the bot token

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```
BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@YourChannelName
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Bot

```bash
python main_bot.py
```

## Deployment (Heroku/Railway)

The bot includes a Flask web server for deployment on platforms that require a web process.

```bash
python site.py
```

This starts both the Flask server (port 5000) and the bot.

## Project Structure

```
TG_BOT/
├── main_bot.py      # Main bot logic
├── settings.py      # Configuration (loads from .env)
├── site.py          # Flask server for deployment
├── requirements.txt # Python dependencies
├── Procfile         # Heroku process file
├── .env.example     # Environment template
└── .gitignore       # Git ignore rules
```

## Requirements

- Python 3.8+
- python-telegram-bot 20.3+
- Flask 2.0+

## License

MIT
