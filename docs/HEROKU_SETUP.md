# Heroku Setup Guide

## Required Config Vars

Set these config vars in your Heroku app's settings:

```
# Required
DISCORD_TOKEN=your_discord_token_here
OPENROUTER_API_KEY=sk-or-v1-xxxx
OPENROUTER_API_BASE=https://openrouter.ai/api/v1

# Web Dashboard Security (Change these!)
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=your_random_secret_key

# Optional Debug Settings
DEBUG=false
LOG_LEVEL=INFO

# Webhooks (Add as many as needed)
DISCORD_WEBHOOK_1=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_2=https://discord.com/api/webhooks/...
```

## Setting Up Config Vars

1. Go to your Heroku dashboard
2. Select your app
3. Go to Settings
4. Click "Reveal Config Vars"
5. Add each variable listed above

## Important Notes

- Never use default passwords in production
- Generate a secure SECRET_KEY (you can use Python's secrets.token_hex(32))
- Set DEBUG=false in production
- Make sure OPENROUTER_API_KEY has sufficient credits
- Webhooks are optional but recommended for model responses

## Database

The SQLite database will be created automatically in the databases directory. Note that on Heroku, any changes to the filesystem are temporary and will be lost on dyno restart. Consider using a proper database add-on for production.

## Checking Configuration

You can verify your configuration by checking the logs:

```bash
heroku logs --tail
```

Look for any configuration errors or warnings during startup.

## Environment Variables Command

You can set all config vars at once using the Heroku CLI:

```bash
heroku config:set \
  DISCORD_TOKEN=your_discord_token_here \
  OPENROUTER_API_KEY=sk-or-v1-xxxx \
  OPENROUTER_API_BASE=https://openrouter.ai/api/v1 \
  ADMIN_USERNAME=your_admin_username \
  ADMIN_PASSWORD=your_secure_password \
  SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))') \
  DEBUG=false \
  LOG_LEVEL=INFO \
  DISCORD_WEBHOOK_1=your_webhook_url_1 \
  DISCORD_WEBHOOK_2=your_webhook_url_2
```

Replace the placeholder values with your actual configuration.
