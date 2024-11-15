"""
Configuration management for SplinterTree bot.
Loads and validates environment variables.
"""
import os
import secrets
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load .env file if it exists
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).parent.parent
DATABASE_DIR = BASE_DIR / 'databases'
LOGS_DIR = BASE_DIR / 'logs'
STATIC_DIR = BASE_DIR / 'static'

# Create necessary directories
DATABASE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN must be set in environment variables")

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY must be set in environment variables")

OPENROUTER_API_BASE = os.getenv('OPENROUTER_API_BASE', 'https://openrouter.ai/api/v1')

# Web Dashboard Configuration
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'change_me_in_production')
if ADMIN_PASSWORD == 'change_me_in_production':
    logging.warning("Using default admin password! Change this in production!")

SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATABASE_DIR}/interaction_logs.db')
DATABASE_PATH = str(DATABASE_DIR / 'interaction_logs.db')

# Context Window Settings
DEFAULT_CONTEXT_WINDOW = 50
MAX_CONTEXT_WINDOW = 500
CONTEXT_WINDOWS = {}  # Will be populated at runtime

# Webhook Configuration
def load_webhooks() -> list:
    """Load Discord webhooks from environment variables"""
    webhooks = []
    i = 1
    while True:
        webhook = os.getenv(f'DISCORD_WEBHOOK_{i}')
        if not webhook:
            break
        webhooks.append(webhook)
        i += 1
    return webhooks

WEBHOOKS = load_webhooks()

# API Headers
def get_openrouter_headers(site_url=None, site_name=None):
    """Get headers for OpenRouter API requests"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    if site_url:
        headers["HTTP-Referer"] = site_url
    if site_name:
        headers["X-Title"] = site_name
    return headers

# File Paths
CONFIG_PATH = BASE_DIR / 'bot_config.json'
STATUS_PATH = BASE_DIR / 'bot_status.txt'
PROMPTS_PATH = BASE_DIR / 'prompts/consolidated_prompts.json'
TEMPERATURES_PATH = BASE_DIR / 'temperatures.json'

# Load Prompts
def load_prompts():
    """Load system prompts from file"""
    if PROMPTS_PATH.exists():
        with open(PROMPTS_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    return "{}"  # Return empty JSON object if file doesn't exist

# Load Temperatures
def load_temperatures():
    """Load temperature settings from file"""
    if TEMPERATURES_PATH.exists():
        with open(TEMPERATURES_PATH, 'r') as f:
            return f.read()
    return "{}"  # Return empty JSON object if file doesn't exist

# Initialize configuration
SYSTEM_PROMPTS = load_prompts()
TEMPERATURES = load_temperatures()

# Validate Configuration
def validate_config():
    """Validate the configuration"""
    errors = []
    
    if not DISCORD_TOKEN:
        errors.append("DISCORD_TOKEN is not set")
    
    if not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY is not set")
    
    if ADMIN_PASSWORD == 'change_me_in_production':
        errors.append("Default admin password is being used")
    
    if not WEBHOOKS:
        logging.warning("No Discord webhooks configured")
    
    if errors:
        for error in errors:
            logging.error(f"Configuration Error: {error}")
        raise ValueError("Invalid configuration. Check logs for details.")

# Validate configuration on import
validate_config()
