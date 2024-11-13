# Webhook Integration

This feature allows LLM responses to be sent through Discord webhooks when messages are prefixed with `!hook`.

## Setup

1. Configure webhook URLs in your `.env` file:
```
DISCORD_WEBHOOK_1=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_2=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_3=https://discord.com/api/webhooks/...
```

You can add multiple webhooks by incrementing the number (DISCORD_WEBHOOK_1, DISCORD_WEBHOOK_2, etc.).

## Usage

Simply prefix any message with `!hook` to send the LLM response through configured webhooks:

```
!hook Tell me a joke
```

The bot will:
1. Process the message through the appropriate LLM cog
2. Send the response to all configured webhooks
3. React with ✅ if successful, or ❌ if there was an error

## Features

- Automatically retries failed webhook deliveries
- Handles rate limiting gracefully
- Supports multiple webhook endpoints
- Maintains original LLM model attribution in responses
- Debug logging for troubleshooting

## Error Handling

The integration includes robust error handling:
- Retries failed webhook deliveries up to 3 times
- Handles Discord rate limits automatically
- Provides visual feedback through reactions
- Logs errors for debugging

## Configuration

Additional settings can be configured in `config/webhook_config.py`:

- `MAX_RETRIES`: Maximum number of retry attempts for failed webhook deliveries (default: 3)
- `WEBHOOK_TIMEOUT`: Timeout for webhook requests in seconds (default: 10)
- `DEBUG_LOGGING`: Enable detailed logging for webhook operations (default: False)
