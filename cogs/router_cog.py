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
            trigger_words=[],  # Remove !activate from trigger_words
            model="mistralai/ministral-3b",
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

        # Track last model used per channel to prevent loops
        self.last_model_used = {}

        # Track handled messages to prevent duplicates
        self.handled_messages = set()

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
            'Ministral': 'MinistralCog',  # Support both spellings
            'Ministeral': 'MinistralCog',  # Support both spellings
            'Liquid': 'LiquidCog',
            'Hermes': 'HermesCog'
        }

        # Create case-insensitive lookup for model names
        self.model_lookup = {k.lower(): k for k in self.model_mapping.keys()}
        logging.debug(f"[Router] Model lookup table: {self.model_lookup}")

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
        # Never handle bot messages
        if message.author.bot:
            logging.debug(f"[Router] Ignoring bot message from {message.author.name}")
            return False

        # Never handle messages from self
        if message.author.id == self.bot.user.id:
            logging.debug("[Router] Ignoring own message")
            return False

        # Skip if message already handled
        if message.id in self.handled_messages:
            logging.debug(f"[Router] Skipping already handled message {message.id}")
            return False

        # Always handle DMs
        if isinstance(message.channel, discord.DMChannel):
            logging.debug("[Router] Handling DM")
            return True

        # Handle if bot is mentioned
        if self.bot.user in message.mentions:
            logging.debug("[Router] Handling mention")
            return True

        # Handle if channel is activated
        if message.channel.id in self.active_channels:
            logging.debug(f"[Router] Handling message in activated channel {message.channel.id}")
            return True

        logging.debug(f"[Router] Not handling message: not DM/mention/activated channel")
        return False

    def check_routing_loop(self, channel_id: int, model_name: str) -> bool:
        """Check if we're in a routing loop"""
        if channel_id in self.last_model_used:
            last_model = self.last_model_used[channel_id]
            consecutive_count = self.last_model_used.get(f"{channel_id}_count", 0)
            
            if last_model == model_name:
                consecutive_count += 1
                if consecutive_count >= 3:  # Three consecutive same routes indicates a loop
                    logging.warning(f"[Router] Detected routing loop to {model_name} in channel {channel_id}")
                    return True
            else:
                consecutive_count = 1
            
            self.last_model_used[f"{channel_id}_count"] = consecutive_count
        
        self.last_model_used[channel_id] = model_name
        return False

    def normalize_model_name(self, raw_model_name: str) -> str:
        """Normalize model name to handle case differences and variations"""
        # Clean up the raw model name
        cleaned_name = raw_model_name.strip().lower()
        
        # Log the normalization process
        logging.debug(f"[Router] Normalizing model name: '{raw_model_name}' -> '{cleaned_name}'")
        logging.debug(f"[Router] Looking up in available models: {list(self.model_lookup.keys())}")
        
        # Look up the canonical model name
        canonical_name = self.model_lookup.get(cleaned_name)
        
        if canonical_name:
            logging.info(f"[Router] Normalized '{raw_model_name}' to '{canonical_name}'")
            return canonical_name
        
        # If not found, try some common variations
        variations = {
            'ministral': 'Ministral',
            'ministeral': 'Ministral',
            'mistral': 'Ministral'
        }
        if cleaned_name in variations:
            canonical_name = variations[cleaned_name]
            logging.info(f"[Router] Normalized variation '{raw_model_name}' to '{canonical_name}'")
            return canonical_name
            
        logging.warning(f"[Router] Could not normalize model name '{raw_model_name}', falling back to Liquid")
        return 'Liquid'

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
                    logging.debug(f"[Router] Got context: {context[:200]}...")
                except Exception as e:
                    logging.error(f"[Router] Error getting context: {str(e)}")

            # Format the routing prompt
            routing_prompt = f"""### MODEL ROUTER v4.2 ###
Message: "{message.content}"
Context: "{context}"

# MODEL PATHS 
[DO NOT OUTPUT PATHS - INTERNAL ONLY]
{{VISION}}
Llama32_11b:  basic vision
Llama32_90b:  complex vision

{{TECHNICAL}}
Goliath:      advanced tech
Nemotron:     complex tech
Noromaid:     problem solving
Rplus:        commands

{{CREATIVE}}
Pixtral:      creative
Mixtral:      content
Claude3Haiku: poetry
Magnum:       advanced creative

{{ANALYSIS}}
Gemini:       formal multilingual
Sonar:        detailed support
Sydney:       emotional advanced
Inferor:      basic support

{{GENERAL}}
OpenChat:     community
Dolphin:      multitask
Gemma:        language
Ministral:    general
Liquid:       fluid
Hermes:       personal
Router:       routing

[INTERNAL ONLY - DO NOT OUTPUT]:
1. Check vision
2. Check technical
3. Check creative
4. Check analysis
5. Check general
6. Apply overrides

# OUTPUT FORMAT
Return exactly ONE model ID with no explanation:
Gemini, Magnum, Sonar, Sydney, Goliath, Pixtral, 
Mixtral, Claude3Haiku, Inferor, Nemotron, Noromaid, 
Rplus, Router, Llama32_11b, Llama32_90b, OpenChat, 
Dolphin, Gemma, Ministral, Liquid, Hermes

Model ID:"""

            # Add image presence info
            has_image = self.has_image_attachments(message)
            if has_image:
                routing_prompt = f"Note: Message contains image attachments.\n\n{routing_prompt}"
                logging.debug("[Router] Message contains image attachments")

            # Call OpenRouter API for inference
            messages = [
                {"role": "system", "content": "You are a message routing assistant. Follow the routing protocol exactly."},
                {"role": "user", "content": routing_prompt}
            ]

            logging.debug(f"[Router] Calling OpenRouter API for message: {message.content[:100]}...")
            response = await self.api_client.call_openrouter(
                messages=messages,
                model=self.model,
                temperature=0.3,  # Low temperature for more consistent routing
                stream=False,
                user_id=str(message.author.id),
                guild_id=str(message.guild.id) if message.guild else None
            )

            if response and 'choices' in response:
                raw_model_name = response['choices'][0]['message']['content'].strip()
                logging.debug(f"[Router] Raw model name from API: {raw_model_name}")
                
                # Normalize the model name
                model_name = self.normalize_model_name(raw_model_name)
                
                # Check for routing loops
                if self.check_routing_loop(message.channel.id, model_name):
                    logging.warning(f"[Router] Breaking routing loop, falling back to Liquid")
                    return 'Liquid'
                
                logging.info(f"[Router] Determined route: {model_name} for message: {message.content[:100]}...")
                return model_name

            logging.error("[Router] Invalid response format from OpenRouter")
            logging.debug(f"[Router] Full API response: {response}")
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
        # Clear any loop detection state
        self.last_model_used.pop(channel_id, None)
        self.last_model_used.pop(f"{channel_id}_count", None)
        await ctx.send("RouterCog has been deactivated in this channel.")
        logging.info(f"[Router] Deactivated in channel {channel_id}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle all incoming messages"""
        # Skip if message is from a bot
        if message.author.bot:
            logging.debug(f"[Router] Ignoring bot message from {message.author.name}")
            return

        # Skip if message is a command
        if message.content.startswith('!'):
            return

        # Check if we should handle this message
        if not self.should_handle_message(message):
            return

        try:
            # Mark message as handled
            self.handled_messages.add(message.id)

            # Log message details for debugging
            channel_type = "DM" if isinstance(message.channel, discord.DMChannel) else "guild"
            logging.debug(f"[Router] Processing message: channel_type={channel_type}, "
                        f"channel_id={message.channel.id}, "
                        f"author={message.author.name}, "
                        f"content={message.content[:100]}...")

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
