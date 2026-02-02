# Telegram Post Scheduler Bot

A Telegram bot that allows users to schedule posts to channels and groups.

## Features

- Schedule posts for one-time or daily delivery
- **Batch scheduling** - schedule multiple posts at once
- **Edit scheduled posts** - modify text or time without deleting
- Works in **private chats**, **public groups**, and **private groups**
- In private chat: posts to the configured channel
- In groups: posts directly to that group
- View and manage scheduled posts
- Daily welcome message on first interaction
- **Admin dashboard** - stats for bot owner

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and help |
| `/schedule` | Schedule a new post |
| `/batch` | Schedule multiple posts at once |
| `/list` | View your scheduled posts |
| `/edit` | Edit a scheduled post (text or time) |
| `/delete` | Delete a scheduled post |
| `/admin` | Admin dashboard (owner only) |
| `/cancel` | Cancel current operation |

## Usage

### In Private Chat
1. Message the bot directly
2. Use `/schedule` to create a post
3. The post will be sent to the configured `CHANNEL_ID`

### In Groups
1. Add the bot to your group
2. Use `/schedule` in the group chat
3. The post will be sent to that group

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

### 5. Adding to Groups

1. Open your bot's settings in [@BotFather](https://t.me/BotFather)
2. Use `/setjoingroups` and enable group joining
3. Add the bot to your group
4. Make the bot an **admin** so it can post messages

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

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Telegram bot token from BotFather |
| `CHANNEL_ID` | Yes | Default channel (`@name` or numeric ID) |
| `ADMIN_ID` | No | Your Telegram user ID for `/admin` command |
| `LOG_LEVEL` | No | Logging level (default: `INFO`) |

## Requirements

- Python 3.10+
- python-telegram-bot 20.3+
- Flask 3.0+

## License

MIT
