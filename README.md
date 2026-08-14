# Emmanuel Digitals & CO — Telegram Agency Bot

Professional Telegram intake bot for **Emmanuel Digitals & CO**.

## Features

- Branded `/start` home menu
- About Agency section
- Services section
- Portfolio external Telegram button
- Simple client request flow
- Forwards the user's original message directly to the admin chat
- Includes client name, username, Telegram ID, and timestamp
- Supports text, photos, documents, and other Telegram message types through message copying
- Back to Home navigation
- `/help` and `/cancel`
- Configuration through environment variables

## Environment variables

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_CHAT_ID=your_admin_chat_id
PORTFOLIO_URL=https://t.me/your_portfolio_channel
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python bot.py
```

Never commit your real `BOT_TOKEN` or admin chat ID to GitHub.
