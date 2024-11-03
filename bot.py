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
from datetime import datetime, timedelta, timezone
import re
import pytz
import traceback

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)

# Set up bot
TOKEN = config.DISCORD_TOKEN
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in config.py.")

# Get the absolute path to the bot directory
BOT_DIR = os.path.dirname(os.path.abspath(__file__))

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.typing = True
intents.dm_messages = True
intents.guilds = True
intents.members = True

# Initialize bot with a default command prefix
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Store loaded cogs for random selection
loaded_cogs = []

# Store message history
message_history = {}

# Track bot statistics
start_time = None
last_interaction = {
    'user': None,
    'time': None
}

# Keep track of last used cog per channel
last_used_cogs = {}

# Track processed messages to prevent double handling
processed_messages = set()

# Flag to track if cogs have been set up
cogs_setup_complete = False

# File to persist processed messages
PROCESSED_MESSAGES_FILE = os.path.join(BOT_DIR, 'processed_messages.json')

def load_processed_messages():
    """Load processed messages from file"""
    global processed_messages
    if os.path.exists(PROCESSED_MESSAGES_FILE):
        try:
            with open(PROCESSED_MESSAGES_FILE, 'r') as f:
                processed_messages = set(json.load(f))
            logging.info(f"Loaded {len(processed_messages)} processed messages from file")
        except Exception as e:
            logging.error(f"Error loading processed messages: {str(e)}")

def save_processed_messages():
    """Save processed messages to file"""
    try:
        with open(PROCESSED_MESSAGES_FILE, 'w') as f:
            json.dump(list(processed_messages), f)
        logging.info(f"Saved {len(processed_messages)} processed messages to file")
    except Exception as e:
        logging.error(f"Error saving processed messages: {str(e)}")

def get_history_file(channel_id: str) -> str:
    """Get the history file path for a channel"""
    history_dir = os.path.join(BOT_DIR, 'history')
    if not os.path.exists(history_dir):
        os.makedirs(history_dir)
    return os.path.join(history_dir, f'history_{channel_id}.json')

def get_uptime():
    """Get bot uptime as a formatted string"""
    if start_time is None:
        return "Unknown"
    pst = pytz.timezone('US/Pacific')
    current_time = datetime.now(pst)
    uptime = current_time - start_time.astimezone(pst)
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

async def unload_all_cogs():
    """Unload all currently loaded cogs"""
    for extension in list(bot.extensions):
        try:
            await bot.unload_extension(extension)
            logging.info(f"Unloaded extension: {extension}")
        except Exception as e:
            logging.error(f"Error unloading extension {extension}: {str(e)}")

async def setup_cogs():
    """Load all cogs"""
    global loaded_cogs, cogs_setup_complete

    # Prevent multiple setups
    if cogs_setup_complete:
        logging.info("Cogs already set up, skipping setup")
        return

    # Reset loaded cogs list and unload any existing cogs
    loaded_cogs = []
    await unload_all_cogs()

    # Load context settings
    await load_context_settings()

    # First load Llama32_3B cog since it's needed for summarization
    try:
        await bot.load_extension('cogs.llama32_3b_cog')
        logging.info("Loaded Llama32_3B cog for summarization")
    except Exception as e:
        logging.error(f"Failed to load Llama32_3B cog: {str(e)}")
        logging.error(traceback.format_exc())

    # Then load core cogs
    core_cogs = ['settings_cog', 'context_cog', 'management_cog']
    for cog in core_cogs:
        try:
            await bot.load_extension(f'cogs.{cog}')
            logging.info(f"Loaded core cog: {cog}")
        except Exception as e:
            logging.error(f"Failed to load core cog {cog}: {str(e)}")
            logging.error(traceback.format_exc())

    # Then load all model cogs
    cogs_dir = os.path.join(BOT_DIR, 'cogs')
    for filename in os.listdir(cogs_dir):
        if filename.endswith('_cog.py') and filename not in ['base_cog.py', 'llama32_3b_cog.py'] + [f"{cog}.py" for cog in core_cogs + ['help_cog']]:
            try:
                module_name = filename[:-3]  # Remove .py
                logging.debug(f"Attempting to load cog: {module_name}")
                
                # Load the cog extension using importlib
                cog_module = importlib.import_module(f"cogs.{module_name}")
                
                # Get the cog class from the module
                cog_class = getattr(cog_module, module_name.capitalize())
                
                # Instantiate the cog and add it to the bot
                cog_instance = cog_class(bot)
                bot.add_cog(cog_instance)
                
                loaded_cogs.append(cog_instance)
                logging.info(f"Loaded cog: {cog_instance.name}")
                
            except Exception as e:
                logging.error(f"Failed to load cog {filename}: {str(e)}")
                logging.error(traceback.format_exc())

    # Finally load help cog after all other cogs are loaded
    try:
        await bot.load_extension('cogs.help_cog')
        logging.info("Loaded help cog")
        
        # Ensure help command is accessible
        help_cog = bot.get_cog('HelpCog')
        if help_cog:
            logging.info("Help cog loaded successfully")
        else:
            logging.error("Failed to find HelpCog after loading")
    except Exception as e:
        logging.error(f"Failed to load help cog: {str(e)}")
        logging.error(traceback.format_exc())

    logging.info(f"Total loaded cogs: {len(loaded_cogs)}")
    for cog in loaded_cogs:
        logging.debug(f"Available cog: {cog.name} (Vision: {getattr(cog, 'supports_vision', False)})")

    cogs_setup_complete = True

class StatusUpdater:
    def __init__(self, bot):
        self.bot = bot
        self.status_task = None
        self.last_status = None

    async def start(self):
        if self.status_task is None or self.status_task.done():
            self.status_task = asyncio.create_task(self._update_status_loop())
            logging.info("Started status update task")

    async def _update_status_loop(self):
        while True:
            try:
                current_uptime = get_uptime()
                if current_uptime != self.last_status:
                    await self.bot.change_presence(activity=discord.Game(name=f"Up for {current_uptime}"))
                    self.last_status = current_uptime
                    logging.debug(f"Updated status to: Up for {current_uptime}")
            except Exception as e:
                logging.error(f"Error updating status: {str(e)}")
            await asyncio.sleep(10)  # Update every 10 seconds

status_updater = None

@bot.event
async def on_ready():
    global start_time, status_updater
    pst = pytz.timezone('US/Pacific')
    start_time = datetime.now(pst)
    logging.info(f"Bot is ready! Logged in as {bot.user.name}")
    
    # Set initial "Booting..." status
    await bot.change_presence(activity=discord.Game(name="Booting..."))
    
    await setup_cogs()
    
    # Initialize and start the status updater
    if status_updater is None:
        status_updater = StatusUpdater(bot)
        await status_updater.start()

async def resolve_user_id(user_id):
    """Resolve a user ID to a username"""
    user = await bot.fetch_user(user_id)
    return user.name if user else str(user_id)

async def process_attachment(attachment):
    """Process a single attachment and return its content"""
    if attachment.filename.endswith(('.txt', '.md')):
        content = await attachment.read()
        return content.decode('utf-8')
    elif attachment.content_type.startswith('image/'):
        return f"[Image: {attachment.filename}]"
    else:
        return f"[Attachment: {attachment.filename}]"

def get_cog_by_name(name):
    """Get a cog by name or class name"""
    for cog in bot.cogs.values():
        if (hasattr(cog, 'name') and cog.name.lower() == name.lower()) or \
           cog.__class__.__name__.lower() == f"{name.lower()}cog":
            return cog
    return None

def get_model_from_message(content):
    """Extract model name from message content"""
    if content.startswith('[') and ']' in content:
        return content[1:content.index(']')]
    return None

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if message has already been processed
    if message.id in processed_messages:
        return

    # Update last interaction
    last_interaction['user'] = message.author.display_name
    last_interaction['time'] = datetime.now(pytz.timezone('US/Pacific'))

    # Resolve user IDs to usernames
    content_with_usernames = message.content
    for mention in message.mentions:
        content_with_usernames = content_with_usernames.replace(f'<@{mention.id}>', f'@{mention.name}')

    # Process attachments
    attachment_contents = []
    for attachment in message.attachments:
        attachment_content = await process_attachment(attachment)
        attachment_contents.append(attachment_content)

    # Combine message content and attachment contents
    full_content = content_with_usernames
    if attachment_contents:
        full_content += "\n" + "\n".join(attachment_contents)

    # Debug logging for message content and attachments
    logging.debug(f"Received message in channel {message.channel.id}: {full_content}")

    # Process commands first
    await bot.process_commands(message)

    # Check if message is a reply to a bot message
    if message.reference and message.reference.message_id:
        try:
            replied_msg = await message.channel.fetch_message(message.reference.message_id)
            if replied_msg.author == bot.user:
                # Extract model name from the replied message
                model_name = get_model_from_message(replied_msg.content)
                if model_name:
                    # Get corresponding cog
                    cog = get_cog_by_name(model_name)
                    if cog:
                        logging.debug(f"Using {model_name} cog to handle reply")
                        await cog.handle_message(message) # Fixed: Removed full_content
                        processed_messages.add(message.id)
                        save_processed_messages()  # Save processed messages after handling
                        return
        except Exception as e:
            logging.error(f"Error handling reply: {str(e)}")

    # Check for bot mention or keywords
    msg_content = full_content.lower()
    is_pinged = bot.user in message.mentions
    has_keyword = "splintertree" in msg_content

    # Only handle mentions/keywords if no specific trigger was found
    if (is_pinged or has_keyword) or (not content_with_usernames and attachment_contents):
        # Check if Claude2 cog is available
        claude2_cog = get_cog_by_name('Claude-2')
        if claude2_cog:
            await claude2_cog.handle_message(message) # Fixed: Removed full_content
        else:
            # If Claude2 is not available, use a random cog
            if loaded_cogs:  # Only try to use a random cog if there are loaded cogs
                cog = random.choice(loaded_cogs)
                await cog.handle_message(message) # Fixed: Removed full_content
            else:
                logging.error("No cogs available to handle message")

    # Mark message as processed
    processed_messages.add(message.id)
    save_processed_messages()  # Save processed messages after handling

    # Clean up old processed messages (keep last 1000)
    if len(processed_messages) > 1000:
        processed_messages.clear()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # Ignore command not found errors
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"⏳ This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.")
    else:
        logging.error(f"Command error: {str(error)}")
        logging.error(traceback.format_exc())
        await ctx.reply("❌ An error occurred while executing the command.")

# Run bot
if __name__ == "__main__":
    logging.debug("Starting bot...")
    load_processed_messages()  # Load processed messages on startup
    bot.run(TOKEN)
