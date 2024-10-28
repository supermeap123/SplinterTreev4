import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Token
DISCORD_TOKEN = "MTI3MDc2MDU4NzAyMjA0MTA4OA.GJ-hJ2.jVbI_tNZdopKdvb8nnO0KI7e-V_jGT2PvBcVI8"

# OpenRouter Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = "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"

# OpenPipe Configuration for different projects
OPENPIPE_API_URL = "https://api.openpipe.ai/api/v1"
OPENPIPE_API_KEYS = {
    'eos': "opk_1242d45081f88a13687f4fed09b3e5b8c1fb14c9a1",
    'legacy': "opk_a59a567efec81c09db82543eb9be72b5ca41504cba"  # Renamed from 'sydney' to 'legacy'
}
OPENPIPE_API_KEY = OPENPIPE_API_KEYS['eos']  # Default to EOS key

# Context Window Configuration
DEFAULT_CONTEXT_WINDOW = 50  # Default number of messages to keep in context
MAX_CONTEXT_WINDOW = 100    # Maximum allowed context window size
CONTEXT_WINDOWS = {}        # Per-channel context window sizes

# Feature Toggles (changed to global booleans)
SHARED_HISTORY_ENABLED = True
IMAGE_PROCESSING_ENABLED = True

# Logging Configuration
LOG_LEVEL = "DEBUG"
LOG_FORMAT = "%(asctime)s%(msecs)03d - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Error Messages
ERROR_MESSAGES = {
    'credits_depleted': "⚠️ Credits depleted. Please contact the bot administrator.",
    'invalid_api_key': "🔑 Invalid API key. Please contact the bot administrator.",
    'rate_limit': "⏳ Rate limit exceeded. Please try again later.",
    'network_error': "🌐 Network error. Please try again later.",
    'unknown_error': "❌ An error occurred. Please try again later.",
    'reporting_error': "📝 Unable to log interaction, but response was successful."
}

# Keyword Blocklist
# If any of these keywords are found in the conversation history,
# the bot will not engage with that conversation
BLOCKED_KEYWORDS = [
    "nsfw",
    "porn",
    "hentai",
    "sex",
    "nude",
    "explicit",
    "adult",
    "xxx",
    "r18",
    "erotic",
    "lewd",
    "gore",
    "violence",
    "death",
    "suicide",
    "kill",
    "murder",
    "blood",
    "torture",
    "abuse",
    "rape",
    "drugs",
    "cocaine",
    "heroin",
    "meth",
    "illegal",
    "hack",
    "crack",
    "pirate",
    "torrent",
    "warez",
    "stolen",
    "leak",
    "exploit",
]
