import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json
from typing import Optional, Dict, List

class RouterCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Router",
            nickname="Router",
            trigger_words=['!activate'],  # Only trigger on !activate command
            model="mistralai/mistral-3b",
            provider="openrouter",
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
            'Gemini': 'GeminiCog',
            'Magnum': 'MagnumCog',
            'Sonar': 'SonarCog',
            'Sydney': 'SydneyCog',
            'Goliath': 'GoliathCog',
            'Pixtral': 'PixtralCog',
            'Mixtral': 'MixtralCog',
            'Claude3Haiku': 'Claude3HaikuCog',
            'Inferor': 'InferorCog',
            'Nemotron': 'NemotronCog',
            'Noromaid': 'NoromaidCog',
            'Rplus': 'RplusCog',
            'Router': 'RouterCog',
            'Llama32_11b': 'Llama32_11b_Cog',
            'Llama32_90b': 'Llama32_90b_Cog',
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

    def should_handle_message(self, message: discord.Message) -> bool:
        """Determine if the message should be handled by the router"""
        # Always handle DMs
        if isinstance(message.channel, discord.DMChannel):
            return True

        # Handle if bot is mentioned
        if self.bot.user in message.mentions:
            return True

        # Handle if channel is activated
        if message.channel.id in self.active_channels:
            return True

        return False

    async def determine_route(self, message: discord.Message) -> str:
        """Use OpenRouter inference to determine which model to route to"""
        try:
            # Get context from context_cog if available
            context = ""
            if self.context_cog:
                try:
                    history = await self.context_cog.get_context_messages(
                        str(message.channel.id),
                        limit=5,
                        exclude_message_id=str(message.id)
                    )
                    context = "\n".join([msg['content'] for msg in history])
                except Exception as e:
                    logging.error(f"[Router] Error getting context: {str(e)}")

            # Format the routing prompt
            routing_prompt = f"""### COMPREHENSIVE ROUTER PROTOCOL v4.1 ###

Given: "{message.content}", "{context}"

# COMPLETE MODEL CATALOG

1. ANALYSIS & FORMAL
   Gemini:       Advanced analysis, multilingual support
   Magnum:       Advanced content gen, creative writing
   Sonar:        Complex support, detailed explanations
   Sydney:       High-level conversation, personal advice
   Goliath:      Advanced problem-solving, technical detail

2. CREATIVE & CONTENT
   Pixtral:      Creative writing, content generation
   Mixtral:      Content generation, creative tasks
   Claude3Haiku: Poetry, creative writing, concise
   Inferor:      Basic conversation, support tasks

3. TECHNICAL & COMMAND
   Nemotron:     Technical support, complex problems
   Noromaid:     Advanced problem-solving, technical 
   Rplus:        Command execution, specific tasks
   Router:       Message classification, routing

4. VISION SYSTEMS
   Llama32_11b:  Basic image analysis
   Llama32_90b:  Complex image understanding

5. CONVERSATION & GENERAL
   OpenChat:     General conversation, community
   Dolphin:      Multitask conversation handling
   Gemma:        Advanced language understanding
   Ministral:    General conversation, community
   Liquid:       Fluid general conversation
   Hermes:       High-level personal advice

# ROUTING LOGIC

1. VISION CHECK
   IF image_present:
     IF complex_analysis → Llama32_90b
     ELSE → Llama32_11b

2. TECHNICAL SUPPORT
   IF technical_issue:
     IF highly_complex → Goliath
     IF complex → Nemotron
     IF problem_solving → Noromaid
     IF command_based → Rplus

3. CONTENT CREATION
   IF creative_writing:
     IF poetry/concise → Claude3Haiku
     IF content_gen → Pixtral/Mixtral
     IF advanced → Magnum

4. CONVERSATION TYPE
   IF analytical:
     IF multilingual/formal → Gemini
     IF detailed → Sonar
     IF multitask → Dolphin
   IF personal/emotional:
     IF advice → Hermes
     IF complex → Sydney
   IF community:
     IF general → OpenChat
     IF basic → Inferor

5. DEFAULT ROUTES
   IF general_chat → Ministral/Liquid
   IF language_heavy → Gemma
   IF routing_query → Router

# PRIORITY OVERRIDE
1. Vision processing
2. Technical issues
3. Creative tasks
4. Analysis/Support
5. General queries

Return exactly one:
Gemini, Magnum, Sonar, Sydney, Goliath, Pixtral, 
Mixtral, Claude3Haiku, Inferor, Nemotron, Noromaid, 
Rplus, Router, Llama32_11b, Llama32_90b, OpenChat, 
Dolphin, Gemma, Ministral, Liquid, Hermes

Return model:"""

            # Add image presence info
            has_image = self.has_image_attachments(message)
            if has_image:
                routing_prompt = f"Note: Message contains image attachments.\n\n{routing_prompt}"

            # Call OpenRouter API for inference
            messages = [
                {"role": "system", "content": "You are a message routing assistant. Follow the routing protocol exactly."},
                {"role": "user", "content": routing_prompt}
            ]

            response = await self.api_client.call_openrouter(
                messages=messages,
                model=self.model,
                temperature=0.3,  # Low temperature for more consistent routing
                stream=False,
                user_id=str(message.author.id),
                guild_id=str(message.guild.id) if message.guild else None
            )

            if response and 'choices' in response:
                model_name = response['choices'][0]['message']['content'].strip()
                # Clean up response to match exact model names
                model_name = next((name for name in self.model_mapping.keys() 
                                 if name.lower() == model_name.lower()), 'Liquid')
                logging.info(f"[Router] Determined route: {model_name} for message: {message.content[:100]}...")
                return model_name

            logging.error("[Router] Invalid response format from OpenRouter")
            return 'Liquid'  # Default fallback

        except Exception as e:
            logging.error(f"[Router] Error determining route: {str(e)}")
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
        await ctx.send("RouterCog has been activated in this channel. All messages will now be routed to appropriate models.")
        logging.info(f"[Router] Activated in channel {channel_id}")

    @commands.command(name='deactivate')
    @commands.has_permissions(manage_channels=True)
    async def deactivate(self, ctx):
        """Deactivate RouterCog in the current channel."""
        channel_id = ctx.channel.id
        self.active_channels.discard(channel_id)
        await ctx.send("RouterCog has been deactivated in this channel.")
        logging.info(f"[Router] Deactivated in channel {channel_id}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle all incoming messages"""
        # Skip if message is from a bot
        if message.author.bot:
            return

        # Check if this is an activation command
        if message.content.lower() == '!activate':
            ctx = await self.bot.get_context(message)
            if ctx.valid:
                await self.activate(ctx)
            return

        # Check if we should handle this message
        if not self.should_handle_message(message):
            return

        try:
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
