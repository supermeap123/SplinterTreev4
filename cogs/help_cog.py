"""
Help cog providing command documentation and channel management.
Integrates with unified cog for model information and webhook functionality.
"""
import discord
from discord.ext import commands
import logging
import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional
import aiohttp
import asyncio
from config.webhook_config import load_webhooks, MAX_RETRIES, WEBHOOK_TIMEOUT, DEBUG_LOGGING
from config import CONTEXT_WINDOWS, DEFAULT_CONTEXT_WINDOW, MAX_CONTEXT_WINDOW

class HelpCog(commands.Cog, name="Help"):
    """Help commands and channel management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.context_cog = bot.get_cog('ContextCog')
        self.webhooks = load_webhooks()
        self.session = aiohttp.ClientSession()
        self.dynamic_prompts_file = "dynamic_prompts.json"
        self.activated_channels_file = "activated_channels.json"
        self.activated_channels = self.load_activated_channels()
        logging.debug("[Help] Initialized")

    def load_activated_channels(self):
        """Load activated channels from JSON file"""
        try:
            if os.path.exists(self.activated_channels_file):
                with open(self.activated_channels_file, 'r') as f:
                    channels = json.load(f)
                    logging.info(f"[Help] Loaded activated channels: {channels}")
                    return channels
            logging.info("[Help] No activated channels file found, creating new one")
            return {}
        except Exception as e:
            logging.error(f"[Help] Error loading activated channels: {e}")
            return {}

    def save_activated_channels(self):
        """Save activated channels to JSON file"""
        try:
            with open(self.activated_channels_file, 'w') as f:
                json.dump(self.activated_channels, f, indent=4)
            logging.info(f"[Help] Saved activated channels: {self.activated_channels}")
        except Exception as e:
            logging.error(f"[Help] Error saving activated channels: {e}")

    def get_all_models(self):
        """Get all models and their details from the unified cog"""
        models = []
        vision_models = []

        unified_cog = self.bot.get_cog('UnifiedCog')
        if not unified_cog:
            logging.error("[Help] UnifiedCog not found")
            return [], []

        for model_id, config in unified_cog.model_config.items():
            model_info = {
                'name': config['name'],
                'nickname': config.get('nickname', config['name']),
                'trigger_words': config['trigger_words'],
                'supports_vision': config.get('supports_vision', False),
                'model': config['model'],
                'provider': 'openrouter',
                'description': ', '.join(config['keywords']) if 'keywords' in config else ''
            }

            if model_info['supports_vision']:
                vision_models.append(model_info)
            else:
                models.append(model_info)

        return vision_models, models

    def format_model_list(self, vision_models, models):
        """Format the model list for display"""
        help_text = """**🤖 Available AI Models**\n\n"""

        # Add vision-capable models
        if vision_models:
            help_text += "**Vision-Capable Models:**\n"
            for model in vision_models:
                triggers = ", ".join(model['trigger_words'])
                help_text += f"• **{model['name']}** [{model['model']} via {model['provider']}]\n"
                help_text += f"  *Triggers:* {triggers}\n"
                help_text += f"  *Special:* Can analyze images and provide descriptions\n"
                if model['description']:
                    help_text += f"  *Keywords:* {model['description']}\n\n"
                else:
                    help_text += "\n"

        # Add language models
        if models:
            help_text += "**Large Language Models:**\n"
            for model in models:
                triggers = ", ".join(model['trigger_words'])
                help_text += f"• **{model['name']}** [{model['model']} via {model['provider']}]\n"
                help_text += f"  *Triggers:* {triggers}\n"
                if model['description']:
                    help_text += f"  *Keywords:* {model['description']}\n\n"
                else:
                    help_text += "\n"

        return help_text

    def format_simple_model_list(self, vision_models, models):
        """Format a simple model list with just names and models"""
        model_list = "**Available Models:**\n"

        # Add vision models with a 📷 indicator
        for model in vision_models:
            model_list += f"📷 {model['name']} - {model['model']}\n"

        # Add regular models
        for model in models:
            model_list += f"💬 {model['name']} - {model['model']}\n"

        return model_list

    @commands.command(name="help", aliases=["st_help"])
    async def help_command(self, ctx):
        """Send a comprehensive help message with all available features"""
        try:
            # Get dynamically loaded models
            vision_models, models = self.get_all_models()
            model_list = self.format_model_list(vision_models, models)

            help_message = f"""{model_list}
**📝 Special Features:**
• **Multi-Model Support** - Access to various AI models through OpenRouter
• **Streaming Responses** - Real-time response streaming for natural conversation flow
• **Shared Context Database** - Models share conversation history for better context
• **Universal Image Processing** - Automatic image description and analysis
• **File Handling** - Support for text files and images
• **Emotion Analysis** - Reactions based on message sentiment
• **Status Updates** - Rotating status showing uptime and current model
• **Dynamic System Prompts** - Customizable per-channel system prompts with variable support
• **PST Timezone Preference** - All time-related operations use Pacific Standard Time (PST)
• **User ID Resolution** - Automatically resolves Discord user IDs to usernames
• **Attachment Processing** - Handles images and text files
• **Webhook Integration** - Send responses through Discord webhooks
• **Flexible Context Window** - Adjustable context size from 50 to 500 messages

**💡 Tips:**
1. Models respond to their trigger words or when mentioned
2. Each model has unique strengths - check their keywords
3. Images are automatically analyzed by vision-capable models
4. Use `!setcontext` to adjust conversation history length
5. Use `!activate` to make the bot respond to all messages
6. Use `!hook` to send responses through webhooks
7. DMs with the bot are automatically handled

**Available Commands:**
• `!help` - Show this help message
• `!listmodels` - Show all available models (simple list)
• `!list_agents` - Show all available agents with detailed info
• `!set_system_prompt <agent> <prompt>` - Set a custom system prompt for an AI agent
• `!reset_system_prompt <agent>` - Reset an AI agent's system prompt to default
• `!setcontext <size>` - Set context window size (50-500 messages)
• `!getcontext` - View current context window size
• `!resetcontext` - Reset context window to default size
• `!hook <message>` - Send an LLM response through webhooks
• `!activate` - Make bot respond to all messages in current channel
• `!deactivate` - Stop bot from responding to all messages
• `!list_activated` - List all activated channels

**System Prompt Variables:**
When setting custom system prompts, you can use these variables:
• {{MODEL_ID}} - The AI model's name
• {{USERNAME}} - The user's Discord display name
• {{DISCORD_USER_ID}} - The user's Discord ID
• {{TIME}} - Current local time (PST)
• {{TZ}} - Local timezone (PST)
• {{SERVER_NAME}} - Current Discord server name
• {{CHANNEL_NAME}} - Current channel name
"""

            # Send the help message in chunks to avoid exceeding Discord's message length limit
            for msg in [help_message[i:i + 2000] for i in range(0, len(help_message), 2000)]:
                await ctx.send(msg)

            logging.info(f"[Help] Sent help message to user {ctx.author.name}")
        except Exception as e:
            logging.error(f"[Help] Error sending help message: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while fetching the help message. Please try again later.")

    @commands.command(name="listmodels", aliases=["st_listmodels"])
    async def list_models_command(self, ctx):
        """Send a simple list of all available models"""
        try:
            vision_models, models = self.get_all_models()
            model_list = self.format_simple_model_list(vision_models, models)
            await ctx.send(model_list)
            logging.info(f"[Help] Sent model list to user {ctx.author.name}")
        except Exception as e:
            logging.error(f"[Help] Error sending model list: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while fetching the model list. Please try again later.")

    @commands.command(name="list_agents", aliases=["st_list_agents"])
    async def list_agents_command(self, ctx):
        """Send a detailed list of all available agents and their configurations"""
        try:
            vision_models, models = self.get_all_models()
            embed = discord.Embed(title="🤖 Available Agents", color=discord.Color.blue())
            for model in vision_models + models:
                triggers = ", ".join(model['trigger_words'])
                description = f"**Model:** {model['model']} via {model['provider']}\n"
                description += f"**Triggers:** {triggers}\n"
                if model['supports_vision']:
                    description += "*Supports vision and can analyze images.*\n"
                if model['description']:
                    description += f"**Keywords:** {model['description']}\n"
                embed.add_field(name=model['name'], value=description, inline=False)
            await ctx.send(embed=embed)
            logging.info(f"[Help] Sent agent list to user {ctx.author.name}")
        except Exception as e:
            logging.error(f"[Help] Error sending agent list: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while fetching the agent list. Please try again later.")

    @commands.command(name='hook')
    async def hook_command(self, ctx, *, content: str = None):
        """Send a message through configured webhooks"""
        if not content:
            await ctx.reply("❌ Please provide a message after !hook")
            return

        if DEBUG_LOGGING:
            logging.info(f"[Help] Processing hook command: {content}")

        # Create a copy of the message with the content
        message = discord.Message.__new__(discord.Message)
        message.__dict__.update(ctx.message.__dict__)
        message.content = content

        # Get unified cog
        unified_cog = self.bot.get_cog('UnifiedCog')
        if not unified_cog:
            await ctx.reply("❌ UnifiedCog not found")
            return

        try:
            # Let unified cog handle the message
            await unified_cog.handle_message(message)
            await ctx.message.add_reaction('✅')
        except Exception as e:
            logging.error(f"[Help] Error processing hook command: {e}")
            await ctx.message.add_reaction('❌')
            await ctx.reply("❌ Failed to process message")

    @commands.command(name="set_system_prompt", aliases=["st_set_system_prompt"])
    @commands.has_permissions(manage_messages=True)
    async def set_system_prompt(self, ctx, agent: str, *, prompt: str):
        """Set a custom system prompt for an AI agent in this channel"""
        try:
            # Load existing prompts
            if os.path.exists(self.dynamic_prompts_file):
                with open(self.dynamic_prompts_file, "r") as f:
                    dynamic_prompts = json.load(f)
            else:
                dynamic_prompts = {}

            # Get guild and channel IDs
            guild_id = str(ctx.guild.id) if ctx.guild else None
            channel_id = str(ctx.channel.id)

            # Initialize guild dict if needed
            if guild_id and guild_id not in dynamic_prompts:
                dynamic_prompts[guild_id] = {}

            # Set the prompt
            if guild_id:
                if channel_id not in dynamic_prompts[guild_id]:
                    dynamic_prompts[guild_id][channel_id] = {}
                dynamic_prompts[guild_id][channel_id][agent] = prompt
            else:
                if channel_id not in dynamic_prompts:
                    dynamic_prompts[channel_id] = {}
                dynamic_prompts[channel_id][agent] = prompt

            # Save updated prompts
            with open(self.dynamic_prompts_file, "w") as f:
                json.dump(dynamic_prompts, f, indent=4)

            await ctx.reply(f"✅ System prompt updated for {agent} in this channel.")

        except Exception as e:
            logging.error(f"Error setting system prompt: {str(e)}")
            await ctx.reply("❌ Failed to set system prompt. Please try again.")

    @commands.command(name="reset_system_prompt", aliases=["st_reset_system_prompt"])
    @commands.has_permissions(manage_messages=True)
    async def reset_system_prompt(self, ctx, agent: str):
        """Reset the system prompt for an AI agent to its default in this channel"""
        try:
            if not os.path.exists(self.dynamic_prompts_file):
                await ctx.reply("No custom prompts found.")
                return

            with open(self.dynamic_prompts_file, "r") as f:
                dynamic_prompts = json.load(f)

            guild_id = str(ctx.guild.id) if ctx.guild else None
            channel_id = str(ctx.channel.id)

            # Remove prompt if it exists
            if guild_id and guild_id in dynamic_prompts:
                if channel_id in dynamic_prompts[guild_id]:
                    if agent in dynamic_prompts[guild_id][channel_id]:
                        del dynamic_prompts[guild_id][channel_id][agent]
                    if not dynamic_prompts[guild_id][channel_id]:
                        del dynamic_prompts[guild_id][channel_id]
                if not dynamic_prompts[guild_id]:
                    del dynamic_prompts[guild_id]
            elif channel_id in dynamic_prompts:
                if agent in dynamic_prompts[channel_id]:
                    del dynamic_prompts[channel_id][agent]
                if not dynamic_prompts[channel_id]:
                    del dynamic_prompts[channel_id]

            # Save updated prompts
            with open(self.dynamic_prompts_file, "w") as f:
                json.dump(dynamic_prompts, f, indent=4)

            await ctx.reply(f"✅ System prompt reset to default for {agent} in this channel.")

        except Exception as e:
            logging.error(f"Error resetting system prompt: {str(e)}")
            await ctx.reply("❌ Failed to reset system prompt. Please try again.")

    async def send_to_webhook(self, webhook_url: str, content: str, retries: int = 0) -> bool:
        """Send content to a Discord webhook"""
        if retries >= MAX_RETRIES:
            logging.error(f"[Help] Max retries reached for webhook")
            return False

        try:
            async with self.session.post(
                webhook_url,
                json={"content": content},
                timeout=WEBHOOK_TIMEOUT
            ) as response:
                if response.status == 429:  # Rate limited
                    retry_after = float(response.headers.get('Retry-After', 5))
                    await asyncio.sleep(retry_after)
                    return await self.send_to_webhook(webhook_url, content, retries + 1)
                
                return 200 <= response.status < 300

        except asyncio.TimeoutError:
            logging.warning(f"[Help] Webhook request timed out, retrying...")
            return await self.send_to_webhook(webhook_url, content, retries + 1)
        except Exception as e:
            logging.error(f"[Help] Error sending to webhook: {str(e)}")
            return False

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        asyncio.create_task(self.session.close())

async def setup(bot):
    try:
        # Remove default help command
        bot.remove_command('help')
        cog = HelpCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Help] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Help] Failed to register cog: {e}", exc_info=True)
        raise
