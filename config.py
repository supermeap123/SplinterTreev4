import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord bot token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# OpenPipe API key
OPENPIPE_API_KEY = os.getenv('OPENPIPE_API_KEY')

# OpenPipe API URL
OPENPIPE_API_URL = os.getenv('OPENPIPE_API_URL', 'https://api.openpipe.ai/v1')

# Logging level
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Context windows (can be updated dynamically)
CONTEXT_WINDOWS = {}

# Other configuration variables can be added here as needed
