"""
SplinterTree Discord bot with configuration validation.
"""
import discord
from discord.ext import commands, tasks
import logging
import os
import config
import importlib
import asyncio
import random
import aiohttp
import json
from datetime import datetime, timedelta
import pytz
import traceback
from shared.api import api  # Import the API singleton
import sys
import requests

def validate_config():
    """Validate configuration before starting"""
    errors = []
    warnings = []

    # Check required environment variables
    required_vars = [
        'DISCORD_TOKEN',
        'OPENROUTER_API_KEY',
        'ADMIN_USERNAME',
        'ADMIN_PASSWORD',
        'SECRET_KEY'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")

    # Test Discord token
    token = os.getenv('DISCORD_TOKEN')
    if token:
        try:
            response = requests.get(
                'https://discord.com/api/v9/users/@me',
                headers={'Authorization': f'Bot {token}'}
            )
            if response.status_code != 200:
                errors.append(f"Invalid Discord token (Status: {response.status_code})")
        except Exception as e:
            errors.append(f"Error testing Discord token: {str(e)}")

    # Test OpenRouter API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    if api_key:
        try:
            response = requests.get(
                'https://openrouter.ai/api/v1/auth/key',
                headers={'Authorization': f'Bearer {api_key}'}
            )
            if response.status_code != 200:
                errors.append(f"Invalid OpenRouter API key (Status: {response.status_code})")
        except Exception as e:
            errors.append(f"Error testing OpenRouter API key: {str(e)}")

    # Check security settings
    if os.getenv('ADMIN_PASSWORD') == 'change_me_in_production':
        warnings.append("Using default admin password")
    
    if os.getenv('DEBUG', 'false').lower() == 'true':
        warnings.append("Debug mode is enabled")

    # Print warnings
    for warning in warnings:
        logging.warning(f"Configuration Warning: {warning}")

    # If there are errors, exit
    if errors:
        for error in errors:
            logging.error(f"Configuration Error: {error}")
        sys.exit(1)

    logging.info("Configuration validation successful")

# Define BOT_DIR as the current working directory
BOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/bot.log')
    ]
)

# Set up intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.typing = True
intents.dm_messages = True
intents.guilds = True
intents.members = True

class SplinterTreeBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processed_messages = set()
        self.api_client = api
        self.loaded_cogs = []
        self.message_history = {}
        self.last_used_cogs = {}
        self.start_time = None
        self.last_interaction = {
            'user': None,
            'time': None
        }
        self.cogs_loaded = False
        self.last_status_check = 0
        self.current_status = None

    async def process_commands(self, message):
        ctx = await self.get_context(message)
        await self.invoke(ctx)

    def get_uptime_enabled(self):
        """Get uptime status toggle state"""
        try:
            with open('bot_config.json', 'r') as f:
                config_data = json.load(f)
                return config_data.get('uptime_enabled', True)
        except:
            return True

    async def check_status_file(self):
        """Check if there's a new status to set"""
        try:
            if not os.path.exists('bot_status.txt'):
                return
            
            mod_time = os.path.getmtime('bot_status.txt')
            if mod_time <= self.last_status_check:
                return
            
            with open('bot_status.txt', 'r') as f:
                status = f.read().strip()
            
            if status:
                self.current_status = status
                await self.change_presence(activity=discord.Game(name=status))
                self.last_status_check = mod_time
                
                with open('bot_status.txt', 'w') as f:
                    f.write('')
                
        except Exception as e:
            logging.error(f"Error checking status file: {e}")

async def load_context_settings():
    """Load saved context window settings"""
    try:
        settings_file = os.path.join(BOT_DIR, 'context_windows.json')
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                config.CONTEXT_WINDOWS.update(settings)
                logging.info("Loaded context window settings")
    except Exception as e:
        logging.error(f"Error loading context settings: {str(e)}")

async def setup_cogs(bot: SplinterTreeBot):
    """Load all cogs"""
    if bot.cogs_loaded:
        logging.info("Cogs have already been loaded. Skipping setup.")
        return

    bot.loaded_cogs = []

    # Load context settings
    await load_context_settings()

    # Load core cogs
    core_cogs = ['context_cog', 'management_cog', 'unified_cog']
    
    for cog in core_cogs:
        try:
            await bot.load_extension(f'cogs.{cog}')
            logging.info(f"Loaded core cog: {cog}")
            
            # Add to loaded_cogs if it has handle_message
            cog_instance = bot.get_cog(cog.split('_')[0].capitalize() + 'Cog')
            if cog_instance and hasattr(cog_instance, 'handle_message'):
                bot.loaded_cogs.append(cog_instance)
                
        except Exception as e:
            logging.error(f"Failed to load core cog {cog}: {str(e)}")
            logging.error(traceback.format_exc())
            sys.exit(1)  # Exit if core cog fails to load

    # Load help cog last (optional)
    try:
        await bot.load_extension('cogs.help_cog')
        logging.info("Loaded help cog")
        
        help_cog = bot.get_cog('HelpCog')
        if not help_cog:
            logging.warning("Failed to find HelpCog after loading, continuing without help commands")
    except Exception as e:
        logging.warning(f"Failed to load help cog: {str(e)}")
        logging.warning("Continuing without help commands")

    logging.info(f"Total loaded cogs with handle_message: {len(bot.loaded_cogs)}")
    bot.cogs_loaded = True

# Initialize bot
bot = SplinterTreeBot(command_prefix='!', intents=intents, help_command=None)

@tasks.loop(seconds=30)
async def update_status():
    """Update bot status"""
    try:
        await bot.check_status_file()
        
        if not bot.current_status and bot.get_uptime_enabled():
            await bot.change_presence(activity=discord.Game(name=f"Up for {get_uptime()}"))
        elif bot.current_status:
            await bot.change_presence(activity=discord.Game(name=bot.current_status))
    except Exception as e:
        logging.error(f"Error updating status: {str(e)}")

async def setup_cogs_task():
    """Load all cogs"""
    await setup_cogs(bot)

@bot.event
async def on_ready():
    pst = pytz.timezone('US/Pacific')
    bot.start_time = datetime.now(pst)
    logging.info(f"Bot is ready! Logged in as {bot.user.name}")
    
    await bot.change_presence(activity=discord.Game(name="Booting..."))
    await setup_cogs_task()
    
    if not update_status.is_running():
        update_status.start()

def get_uptime():
    """Get bot uptime as a formatted string"""
    if bot.start_time is None:
        return "Unknown"
    pst = pytz.timezone('US/Pacific')
    current_time = datetime.now(pst)
    uptime = current_time - bot.start_time.astimezone(pst)
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    bot.last_interaction['user'] = message.author.display_name
    bot.last_interaction['time'] = datetime.now(pytz.timezone('US/Pacific'))

    if message.author == bot.user:
        return

    for cog in bot.cogs.values():
        if hasattr(cog, 'on_message'):
            try:
                await cog.on_message(message)
            except Exception as e:
                logging.error(f"Error in {cog.__class__.__name__}.on_message: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
    else:
        logging.error(f"Command error: {str(error)}")
        logging.error(traceback.format_exc())
        await ctx.reply("❌ An error occurred while executing the command.")

if __name__ == "__main__":
    try:
        # Validate configuration before starting
        validate_config()
        
        # Start the bot
        logging.info("Starting bot...")
        bot.run(config.DISCORD_TOKEN)
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")
        sys.exit(1)
