import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json
import re
from typing import Optional, Dict, List

class RouterCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Router",
            nickname="Router",
            trigger_words=[],
            model="openpipe:FreeRouter-v2-235",
            provider="openpipe",
            prompt_file="router",
            supports_vision=False
        )
        logging.debug(f"[Router] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Router] Using provider: {self.provider}")
        logging.debug(f"[Router] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Router] Failed to load temperatures.json: {e}")
            self.temperatures = {}

        # Initialize set to track active channels
        self.active_channels = set()

        # Model mapping for routing
        self.model_mapping = {
            # Analysis & Formal
            'Gemini': 'GeminiCog',
            'Magnum': 'MagnumCog',
            'Sonar': 'SonarCog',
            'Sydney': 'SydneyCog',
            'Goliath': 'GoliathCog',
            # Creative & Content
            'Pixtral': 'PixtralCog',
            'Mixtral': 'MixtralCog',
            'Claude3Haiku': 'Claude3HaikuCog',
            'Inferor': 'InferorCog',
            # Technical & Command
            'Nemotron': 'NemotronCog',
            'Noromaid': 'NoromaidCog',
            'Rplus': 'RplusCog',
            'Router': 'RouterCog',
            # Vision Systems
            'Llama32_11b': 'Llama32_11b_Cog',
            'Llama32_90b': 'Llama32_90b_Cog',
            # Conversation & General
            'OpenChat': 'OpenChatCog',
            'Dolphin': 'DolphinCog',
            'Gemma': 'GemmaCog',
            'Ministral': 'MinistralCog',
            'Liquid': 'LiquidCog',
            'Hermes': 'HermesCog'
        }

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Router"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    def has_image_attachments(self, message: discord.Message) -> bool:
        """Check if message contains image attachments"""
        if message.attachments:
            return any(att.content_type and att.content_type.startswith('image/') for att in message.attachments)
        return False

    def has_code_blocks(self, content: str) -> bool:
        """Check if message contains code blocks"""
        return bool(re.search(r'```[\w]*\n[\s\S]*?\n```', content))

    def is_technical_query(self, content: str) -> bool:
        """Check if message appears to be a technical query"""
        technical_indicators = [
            r'\b(?:error|bug|issue|problem|crash|fail)\b',
            r'\b(?:code|function|method|api|database|server)\b',
            r'\b(?:how to|how do I|help with)\b.*\b(?:implement|configure|setup|install)\b',
            r'```[\w]*\n[\s\S]*?\n```',  # Code blocks
            r'\b(?:npm|pip|git|docker)\b'
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in technical_indicators)

    def is_creative_request(self, content: str) -> bool:
        """Check if message appears to be a creative request"""
        creative_indicators = [
            r'\b(?:write|create|generate|compose)\b',
            r'\b(?:story|poem|article|blog|content)\b',
            r'\b(?:creative|artistic|imaginative)\b'
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in creative_indicators)

    def is_analytical_query(self, content: str) -> bool:
        """Check if message appears to be an analytical query"""
        analytical_indicators = [
            r'\b(?:analyze|analyse|explain|understand|compare)\b',
            r'\b(?:what is|what are|why does|how does)\b',
            r'\b(?:difference between|relationship|correlation)\b'
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in analytical_indicators)

    def is_personal_query(self, content: str) -> bool:
        """Check if message appears to be a personal/emotional query"""
        personal_indicators = [
            r'\b(?:feel|feeling|felt|emotion|emotional)\b',
            r'\b(?:advice|help me|should I|what should)\b',
            r'\b(?:relationship|personal|private)\b',
            r'(?:😊|😢|😭|😔|😕|🙁|☹️|😣|😖|😫|😩|🥺|😢|😭|😤|😠|😡|🤬|🥰|😍|🤗|😘)'
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in personal_indicators)

    async def determine_route(self, message: discord.Message) -> str:
        """Determine which model/cog to route the message to based on content analysis"""
        content = message.content.lower()
        has_image = self.has_image_attachments(message)

        # 1. VISION CHECK
        if has_image:
            if len(content) > 100 or self.is_analytical_query(content):
                return 'Llama32_90b'
            return 'Llama32_11b'

        # 2. TECHNICAL SUPPORT
        if self.is_technical_query(content):
            if self.has_code_blocks(content) or len(content) > 500:
                return 'Goliath'
            if 'error' in content or 'bug' in content:
                return 'Nemotron'
            if 'how to' in content or 'help with' in content:
                return 'Noromaid'
            if any(cmd in content for cmd in ['npm', 'pip', 'git', 'docker']):
                return 'Rplus'

        # 3. CONTENT CREATION
        if self.is_creative_request(content):
            if 'poem' in content or len(content) < 100:
                return 'Claude3Haiku'
            if 'article' in content or 'blog' in content:
                return 'Pixtral'
            if len(content) > 300:
                return 'Magnum'
            return 'Mixtral'

        # 4. CONVERSATION TYPE
        if self.is_analytical_query(content):
            if re.search(r'[^\x00-\x7F]', content):  # Non-ASCII characters
                return 'Gemini'
            if len(content) > 200:
                return 'Sonar'
            return 'Dolphin'

        if self.is_personal_query(content):
            if 'advice' in content or 'should I' in content:
                return 'Hermes'
            return 'Sydney'

        # 5. DEFAULT ROUTES
        if len(content) > 300:
            return 'Gemma'
        if re.search(r'[^\x00-\x7F]', content):  # Non-ASCII characters
            return 'Ministral'
        
        return 'Liquid'  # Default fallback

    async def route_to_cog(self, message: discord.Message, model_name: str) -> None:
        """Route the message to the appropriate cog"""
        try:
            cog_name = self.model_mapping.get(model_name)
            if not cog_name:
                logging.error(f"[Router] No cog mapping found for model: {model_name}")
                return

            cog = self.bot.get_cog(cog_name)
            if not cog:
                logging.error(f"[Router] Cog not found: {cog_name}")
                return

            logging.info(f"[Router] Routing message to {cog_name}")
            await cog.handle_message(message)

        except Exception as e:
            logging.error(f"[Router] Error routing to cog: {str(e)}")
            await message.channel.send(f"❌ Error routing message: {str(e)}")

    @commands.command(name='activate')
    @commands.has_permissions(manage_channels=True)
    async def activate(self, ctx):
        """Activate RouterCog in the current channel."""
        channel_id = ctx.channel.id
        self.active_channels.add(channel_id)
        await ctx.send("RouterCog has been activated in this channel.")
        logging.info(f"[Router] Activated in channel {channel_id}")

    @commands.command(name='deactivate')
    @commands.has_permissions(manage_channels=True)
    async def deactivate(self, ctx):
        """Deactivate RouterCog in the current channel."""
        channel_id = ctx.channel.id
        self.active_channels.discard(channel_id)
        await ctx.send("RouterCog has been deactivated in this channel.")
        logging.info(f"[Router] Deactivated in channel {channel_id}")

    async def handle_message(self, message):
        """Handle incoming messages when RouterCog is activated."""
        try:
            if message.channel.id not in self.active_channels:
                return

            # Determine which model to route to
            model_name = await self.determine_route(message)
            logging.info(f"[Router] Determined route: {model_name} for message: {message.content[:100]}...")

            # Route the message to the appropriate cog
            await self.route_to_cog(message, model_name)

        except Exception as e:
            logging.error(f"[Router] Error handling message: {str(e)}")
            await message.channel.send(f"❌ Error processing message: {str(e)}")

    async def cog_check(self, ctx):
        """Ensure that commands are only used in guilds."""
        return ctx.guild is not None

async def setup(bot):
    try:
        cog = RouterCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Router] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Router] Failed to register cog: {e}", exc_info=True)
        raise
