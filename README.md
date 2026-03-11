# Discord RSS Alert Bot

Monitors RSS/Atom feeds and posts new items to a Discord channel via webhook. No bot token, no OAuth — just a webhook URL.

## Features

- Supports RSS 2.0 and Atom feeds
- Duplicate detection — never reposts the same item
- Rich Discord embeds with title, link, description, and timestamp
- Configurable max posts per run (prevents spam on first run)
- Rate-limit safe (1 second delay between Discord posts)
- Zero external dependencies — pure Python standard library

## Setup

**1. Create a Discord Webhook**
- Go to your Discord channel → Edit Channel → Integrations → Webhooks → New Webhook
- Copy the webhook URL

**2. Configure**
```bash
cp config.example.json config.json
# Edit config.json with your webhook URL and desired feeds
```

**3. Run**
```bash
python bot.py
```

**4. Schedule (optional)**

Run every 15 minutes with cron:
```
*/15 * * * * /usr/bin/python3 /path/to/bot.py >> /path/to/bot.log 2>&1
```

## Configuration

| Key | Description |
|-----|-------------|
| `webhook_url` | Your Discord webhook URL |
| `max_new_per_run` | Max new posts per feed per run (default: 5) |
| `feeds` | Array of `{name, url}` objects |

## Requirements

Python 3.9+ — no pip installs needed.
