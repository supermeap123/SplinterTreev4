"""
Configuration for webhook integration.
"""

# List of webhook URLs to send messages to
WEBHOOKS = []

# Maximum number of retries for webhook delivery
MAX_RETRIES = 3

# Timeout for webhook requests in seconds
WEBHOOK_TIMEOUT = 10

# Whether to enable webhook debug logging
DEBUG_LOGGING = False

def load_webhooks():
    """
    Load webhook URLs from environment variables.
    Format: DISCORD_WEBHOOK_1=url1,DISCORD_WEBHOOK_2=url2,...
    """
    import os
    webhooks = []
    i = 1
    while True:
        webhook_url = os.getenv(f'DISCORD_WEBHOOK_{i}')
        if not webhook_url:
            break
        webhooks.append(webhook_url)
        i += 1
    return webhooks
