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
bot = commands.Bot(command_prefix='!', intents=intents)

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
    uptime = datetime.utcnow() - start_time
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

def get_last_interaction():
    """Get last interaction as a formatted string"""
    if last_interaction['user'] is None:
        return "No interactions yet"
    time_diff = datetime.utcnow() - last_interaction['time']
    minutes = int(time_diff.total_seconds() / 60)
    if minutes < 1:
        return f"Just now with {last_interaction['user']}"
    elif minutes < 60:
        return f"{minutes}m ago with {last_interaction['user']}"
    else:
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago with {last_interaction['user']}"
        else:
            days = hours // 24
            return f"{days}d ago with {last_interaction['user']}"

async def save_channel_history(channel_id: str):
    """Save message history for a specific channel"""
    if not config.SHARED_HISTORY_ENABLED:
        return
        
    try:
        history_file = get_history_file(channel_id)
        messages = message_history.get(channel_id, [])
        
        # Convert messages to serializable format
        history_data = [
            {
                'content': msg.content,
                'author': str(msg.author),
                'timestamp': msg.created_at.isoformat(),
                'attachments': [
                    {'url': att.url, 'filename': att.filename}
                    for att in msg.attachments
                ] if msg.attachments else []
            }
            for msg in messages
        ]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
            logging.info(f"Saved history for channel {channel_id}")
    except Exception as e:
        logging.error(f"Error saving history for channel {channel_id}: {str(e)}")

async def load_channel_history(channel_id: str, channel):
    """Load message history for a specific channel"""
    if not config.SHARED_HISTORY_ENABLED:
        return
        
    try:
        # Get actual message history from Discord
        window_size = config.CONTEXT_WINDOWS.get(channel_id, config.DEFAULT_CONTEXT_WINDOW)
        window_size = max(window_size, 50)  # Ensure at least 50 messages are loaded
        
        message_history[channel_id] = []
        try:
            async for msg in channel.history(limit=window_size):
                message_history[channel_id].append(msg)
            
            message_history[channel_id].reverse()  # Reverse to maintain chronological order
            logging.info(f"Loaded {len(message_history[channel_id])} messages for channel {channel_id}")
        except discord.errors.Forbidden:
            logging.warning(f"Missing permissions to load history for channel {channel_id}")
        except Exception as e:
            logging.error(f"Error loading Discord history for channel {channel_id}: {str(e)}")
    except Exception as e:
        logging.error(f"Error in load_channel_history for channel {channel_id}: {str(e)}")

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

async def setup_cogs():
    """Load all cogs"""
    global loaded_cogs
    loaded_cogs = []  # Reset loaded cogs list

    # Load context settings
    await load_context_settings()

    # First load core cogs
    core_cogs = ['context_cog', 'help_cog', 'settings_cog']
    for cog in core_cogs:
        try:
            await bot.load_extension(f'cogs.{cog}')
            logging.info(f"Loaded core cog: {cog}")
        except Exception as e:
            logging.error(f"Failed to load core cog {cog}: {str(e)}", exc_info=True)

    # Then load the Llama 11B cog for vision capabilities
    try:
        await bot.load_extension('cogs.llama32_11b_cog')
        logging.info("Loaded Llama 11B cog for vision capabilities")
        # Verify Llama cog is available
        llama_cog = None
        for cog in bot.cogs.values():
            if isinstance(cog, commands.Cog) and getattr(cog, 'name', '') == 'Llama-3.2-11B':
                llama_cog = cog
                break
        if llama_cog:
            logging.info("Verified Llama 11B cog is available for vision processing")
        else:
            logging.warning("Llama 11B cog not found in loaded cogs - vision processing may be unavailable")
    except Exception as e:
        logging.error(f"Failed to load Llama 11B cog: {str(e)}", exc_info=True)
        logging.warning("Vision processing capabilities will be unavailable")

    # Then load all other cogs
    cogs_dir = os.path.join(BOT_DIR, 'cogs')
    for filename in os.listdir(cogs_dir):
        if filename.endswith('_cog.py') and filename not in ['base_cog.py', 'llama32_11b_cog.py'] + [f"{cog}.py" for cog in core_cogs]:
            try:
                module_name = filename[:-3]  # Remove .py
                await bot.load_extension(f'cogs.{module_name}')
                
                # Get the actual cog instance
                cog = None
                # Convert module_name to expected class name format
                parts = module_name.split('_')
                if len(parts) > 1:
                    # Handle special cases like claude1_1_cog -> Claude1_1Cog
                    class_name = ''.join(part.capitalize() for part in parts[:-1]) + 'Cog'
                else:
                    class_name = parts[0].capitalize() + 'Cog'
                
                # Try to find the cog by checking each loaded cog
                for loaded_cog in bot.cogs.values():
                    if (hasattr(loaded_cog, 'name') and loaded_cog.name == class_name.replace('Cog', '')):
                        cog = loaded_cog
                        break
                
                if cog:
                    loaded_cogs.append(cog)
                    logging.info(f"Loaded cog: {getattr(cog, 'name', class_name)}")
                    logging.debug(f"Added {getattr(cog, 'name', class_name)} to loaded_cogs list")
                else:
                    logging.warning(f"Failed to get cog instance for {module_name}")
            except Exception as e:
                logging.error(f"Failed to load cog {filename}: {str(e)}", exc_info=True)

    logging.info(f"Total loaded cogs: {len(loaded_cogs)}")
    for cog in loaded_cogs:
        logging.debug(f"Available cog: {cog.name} (Vision: {getattr(cog, 'supports_vision', False)})")

async def get_random_cog():
    """Get a random cog from loaded cogs, excluding Llama 11B"""
    cogs = [cog for cog in loaded_cogs if getattr(cog, 'random_enabled', True)]
    if cogs:
        selected = random.choice(cogs)
        logging.debug(f"Selected random cog: {selected.name}")
        return selected
    logging.warning("No cogs available for random selection")
    return None

@tasks.loop(seconds=60)  # Discord rate limit is 5 requests per minute
async def rotate_status():
    """Rotate bot status message"""
    try:
        if not bot.is_ready():
            return

        status_type = random.randint(0, 2)
        
        if status_type == 0:
            # Uptime status
            activity = discord.Game(name=f"Up for {get_uptime()}")
        elif status_type == 1:
            # Last interaction status
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=get_last_interaction()
            )
        else:
            # Random cog status
            if loaded_cogs:
                cog = random.choice(loaded_cogs)
                activity = discord.Game(name=f"with {getattr(cog, 'name', 'Unknown')}")
            else:
                activity = discord.Game(name="Loading...")

        await bot.change_presence(activity=activity)
        logging.debug(f"Updated status to: {activity.name}")
    except Exception as e:
        logging.error(f"Error in rotate_status: {str(e)}")

@bot.event
async def on_ready():
    global start_time
    start_time = datetime.utcnow()
    logging.info(f"Bot is ready! Logged in as {bot.user.name}")
    
    # Set initial "Booting..." status
    await bot.change_presence(activity=discord.Game(name="Booting..."))
    
    # Load history for all channels
    for guild in bot.guilds:
        for channel in guild.text_channels:
            channel_id = str(channel.id)
            await load_channel_history(channel_id, channel)
    
    # Load history for DM channels
    for dm_channel in bot.private_channels:
        channel_id = str(dm_channel.id)
        await load_channel_history(channel_id, dm_channel)
    
    await setup_cogs()
    
    # Start status rotation
    if not rotate_status.is_running():
        rotate_status.start()
        logging.info("Started status rotation task")

    # Set initial uptime status after loading
    await bot.change_presence(activity=discord.Game(name=f"Up for {get_uptime()}"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Update last interaction
    last_interaction['user'] = message.author.display_name
    last_interaction['time'] = datetime.utcnow()

    # Add message to history if shared history is enabled
    if config.SHARED_HISTORY_ENABLED:
        channel_id = str(message.channel.id)
        if channel_id not in message_history:
            message_history[channel_id] = []
        message_history[channel_id].append(message)

        # Trim history if needed
        window_size = config.CONTEXT_WINDOWS.get(channel_id, config.DEFAULT_CONTEXT_WINDOW)
        if len(message_history[channel_id]) > window_size:
            message_history[channel_id] = message_history[channel_id][-window_size:]

    # Debug logging for message content and attachments
    logging.debug(f"Received message in channel {message.channel.id}: {message.content}")
    if message.attachments:
        logging.debug(f"Message has {len(message.attachments)} attachments")
        for att in message.attachments:
            logging.debug(f"Attachment: {att.filename} ({att.content_type})")

    # Process commands first
    await bot.process_commands(message)

    # Check for bot mention or keywords
    msg_content = message.content.lower()
    is_pinged = False

    # Check for direct mention
    for mention in message.mentions:
        if mention.id == bot.user.id:
            is_pinged = True
            break

    # Check for role mention
    if message.role_mentions:
        for role in message.role_mentions:
            if bot.user in role.members:
                is_pinged = True
                break

    # Check for @everyone and @here if bot can see them
    if (message.mention_everyone and 
        message.channel.permissions_for(message.guild.me).read_messages):
        is_pinged = True

    has_keyword = "splintertree" in msg_content

    # Only handle mentions/keywords if no specific trigger was found
    if (is_pinged or has_keyword):
        # Check if any specific model was triggered
        specific_trigger = False
        for cog in bot.cogs.values():
            if hasattr(cog, 'trigger_words'):
                if any(word in msg_content for word in cog.trigger_words):
                    specific_trigger = True
                    break

        # Only use random cog if no specific model was triggered
        if not specific_trigger:
            logging.info(f"Bot triggered by {'mention' if is_pinged else 'keyword'} from {message.author.display_name}")
            cog = await get_random_cog()
            if cog:
                logging.debug(f"Using random cog {cog.name} to handle message")
                try:
                    await cog.handle_message(message)
                except Exception as e:
                    logging.error(f"Error in random cog {cog.name} message handling: {str(e)}", exc_info=True)
            else:
                logging.warning("No cog available to handle message")
                await message.channel.send("Sorry, no models are currently available to handle your request.")

    # Save history if shared history is enabled
    if config.SHARED_HISTORY_ENABLED:
        await save_channel_history(str(message.channel.id))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # Ignore command not found errors
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ You don't have permission to use this command.")
    else:
        logging.error(f"Command error: {str(error)}", exc_info=True)
        await ctx.reply("❌ An error occurred while executing the command.")

# Run bot
if __name__ == "__main__":
    logging.debug("Starting bot...")
    bot.run(TOKEN)
