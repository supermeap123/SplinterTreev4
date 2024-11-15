import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json
from typing import Optional, Dict, List, AsyncGenerator
import re

class RouterCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Router",
            nickname="Router",
            trigger_words=[],
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

        # Keywords that should bypass the router
        self.bypass_keywords = [
            r'\b(use|switch to|try|with)\s+(dolphin|gemini|sonar|sydney|goliath|sonnet|hermes|sorcerer|llama32vision)\b',
            r'\b(dolphin|gemini|sonar|sydney|goliath|sonnet|hermes|sorcerer|llama32vision)\s+(please|now|instead)\b',
            r'^(dolphin|gemini|sonar|sydney|goliath|sonnet|hermes|sorcerer|llama32vision)[,:]\s',
            r'\b(dolphin|gemini|sonar|sydney|goliath|sonnet|hermes|sorcerer|llama32vision)\b'  # Added to catch standalone model names
         ]

        # Model mapping for routing - updated to reflect current cogs
        self.model_mapping = {
            'Dolphin': 'DolphinCog',
            'Gemini': 'GeminiCog',
            'Goliath': 'GoliathCog',
            'Hermes': 'HermesCog',
            'Llama32Vision': 'Llama32VisionCog',
            'Llama405b': 'Llama405bCog',
            'Ministral': 'MinistralCog',
            'Router': 'RouterCog',
            'Sonar': 'SonarCog',
            'Sonnet': 'SonnetCog',
            'Sorcerer': 'SorcererCog',
            'Sydney': 'SydneyCog'
        }

        # Create case-insensitive lookup for model names
        self.model_lookup = {k.lower(): k for k in self.model_mapping.keys()}
        logging.debug(f"[Router] Model lookup table: {self.model_lookup}")

    async def _generate_response(self, message) -> Optional[AsyncGenerator[str, None]]:
        """Override base class method to prevent error message"""
        return None

    def has_bypass_keywords(self, content: str) -> bool:
        """Check if message contains keywords that should bypass routing"""
        content = content.lower()
        for pattern in self.bypass_keywords:
            if re.search(pattern, content, re.IGNORECASE):
                logging.debug(f"[Router] Found bypass keyword pattern: {pattern}")
                return True
        return False

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

        # Skip if message contains bypass keywords
        if self.has_bypass_keywords(message.content):
            logging.debug(f"[Router] Skipping message with bypass keywords: {message.content[:100]}")
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
            'mistral': 'Ministral',
            'llama32_90b': 'Llama32Vision',
            'llama32vision': 'Llama32Vision'
        }
        if cleaned_name in variations:
            canonical_name = variations[cleaned_name]
            logging.info(f"[Router] Normalized variation '{raw_model_name}' to '{canonical_name}'")
            return canonical_name
            
        logging.warning(f"[Router] Could not normalize model name '{raw_model_name}', falling back to Ministral")
        return 'Ministral'

    async def determine_route(self, message: discord.Message) -> str:
        """Use OpenRouter inference to determine which model to route to"""
        try:
            # Get context from context_cog if available
            context = ""
            if self.context_cog:
                try:
                    history = await self.context_cog.get_context_messages(
                        str(message.channel.id) if message.channel else None,
                        limit=5,
                        exclude_message_id=str(message.id)
                    )
                    context = "\n".join([msg['content'] for msg in history])
                    logging.debug(f"[Router] Got context: {context[:200]}...")
                except Exception as e:
                    logging.error(f"[Router] Error getting context: {str(e)}")

            # Format the routing prompt
            routing_prompt = f"""### UNIFIED PRODUCTION ROUTER v9.0 ###
Message: "{message.content}"
Context: "{context}"

[MODEL PATHS & STRENGTHS]

REAL-TIME INFORMATION PATH
└─ Sonar
   ├─ Strengths: Current events, trends, updates
   ├─ Best for: Time-sensitive info, recent changes
   ├─ Context: Modern queries, updates needed
   └─ Priority override: Latest info needs

DIVERSE CONVERSATION PATH
└─ Dolphin
   ├─ Strengths: Uncensored topics, open discussion
   ├─ Best for: Controversial subjects, adult themes
   ├─ Context: Mature conversations
   └─ No content restrictions

MENTAL HEALTH PATH
└─ Hermes
   ├─ Strengths: Crisis support, mental health
   ├─ Best for: Emotional support, crisis intervention
   ├─ Context: Support needs, emergencies
   └─ Priority override: Crisis detection

ROLEPLAY PATHS
├─ Sorcerer
│  ├─ Strengths: Fantasy RP, character immersion
│  ├─ Best for: Standard RP scenes, character play
│  ├─ Context: Fantasy settings, adventures
│  └─ Token sweet spot: 200-800
│
└─ Goliath
   ├─ Strengths: Long-form stories, detailed plots
   ├─ Best for: Extended narratives, complex RP
   ├─ Context: Epic sagas, detailed worlds
   └─ Token sweet spot: >800

EMOTIONAL SUPPORT PATH
└─ Sydney
   ├─ Strengths: Empathy, friendship, companionship
   ├─ Best for: Personal connection, emotional support
   ├─ Context: Friendly chat, daily life
   └─ Priority: High for emotional needs

TECHNICAL PATH
└─ Sonnet
   ├─ Strengths: Code, software engineering
   ├─ Best for: Technical tasks, programming
   ├─ Context: Development, system design
   └─ Token sweet spot: >300

MULTIMODAL PATHS
├─ Gemini
│  ├─ Strengths: Complex vision tasks, detailed analysis
│  ├─ Best for: Advanced image understanding
│  ├─ Context: Complex instructions with images
│  └─ Vision support: Yes
│
└─ Llama32Vision
   ├─ Strengths: Basic vision tasks, simple analysis
   ├─ Best for: Moderate image understanding
   ├─ Context: Simple instructions with images
   └─ Vision support: Yes

[PRIORITY OVERRIDE MATRIX]

1. EMERGENCY OVERRIDES
   ├─ Crisis terms detected → Hermes
   ├─ Mental health flags → Hermes
   ├─ Urgent help needed → Hermes
   └─ Priority: Highest

2. TIME SENSITIVITY
   ├─ Current events → Sonar
   ├─ Recent changes → Sonar
   ├─ Updates needed → Sonar
   └─ Priority: Very High

3. CONTENT SENSITIVITY
   ├─ Adult themes → Dolphin
   ├─ Controversial topics → Dolphin
   ├─ Uncensored discussion → Dolphin
   └─ Priority: High

4. EMOTIONAL SUPPORT
   ├─ Personal issues → Sydney
   ├─ Friendship needs → Sydney
   ├─ Daily life chat → Sydney
   └─ Priority: High

5. ROLEPLAY COMPLEXITY
   ├─ Epic narratives → Goliath
   ├─ Standard RP → Sorcerer
   └─ Priority: Medium

6. TECHNICAL NEEDS
   ├─ Code/Software → Sonnet
   └─ Priority: Medium

7. VISION TASKS
   ├─ Complex → Gemini
   ├─ Simple → Llama32Vision
   └─ Priority: Based on complexity

[SEMANTIC TRIGGERS]

CRISIS KEYWORDS
├─ Mental: [anxiety, depression, suicide, crisis, help]
├─ Emergency: [urgent, emergency, immediate, serious]
└─ Support: [therapy, counseling, support, guidance]

TIME SENSITIVITY
├─ Current: [now, latest, recent, update, news]
├─ Changes: [happening, occurred, developed]
└─ Status: [situation, state, condition]

CONTENT MATURITY
├─ Adult: [nsfw, mature, adult, explicit]
├─ Topics: [controversial, sensitive, uncensored]
└─ Discussion: [debate, argument, opinion]

EMOTIONAL SUPPORT
├─ Personal: [friend, talk, listen, understand]
├─ Life: [daily, routine, experience, feeling]
└─ Connection: [relationship, bond, trust]

ROLEPLAY INDICATORS
├─ Epic: [saga, campaign, adventure, quest]
├─ Standard: [scene, character, action, story]
└─ Setting: [fantasy, world, realm, kingdom]

TECHNICAL MARKERS
├─ Code: [programming, development, software]
├─ Engineering: [system, design, architecture]
└─ Technical: [problem, solution, implement]

[IMPLEMENTATION RULES]

1. Check for crisis/emergency first
2. Evaluate time sensitivity
3. Assess content maturity
4. Consider emotional needs
5. Analyze complexity
6. Check for technical requirements
7. Evaluate vision needs
8. Apply appropriate model

[FINAL OUTPUT RULES]

1. Return ONLY the model name
2. No explanation
3. No context
4. No reasoning
5. Exactly one of:
   Sonar, Dolphin, Hermes, Sorcerer, Goliath,
   Sydney, Sonnet, Gemini, Llama32Vision

Model name:"""

            # Add image presence info
            has_image = self.has_image_attachments(message)
            if has_image:
                routing_prompt = f"Note: Message contains image attachments.\n\n{routing_prompt}"
                logging.debug("[Router] Message contains image attachments")

            # Call OpenRouter API for inference
            messages = [
                {"role": "system", "content": "You are a message routing assistant. Return only the model name."},
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
                    logging.warning(f"[Router] Breaking routing loop, falling back to Ministral")
                    return 'Ministral'
                
                logging.info(f"[Router] Determined route: {model_name} for message: {message.content[:100]}...")
                return model_name

            logging.error("[Router] Invalid response format from OpenRouter")
            logging.debug(f"[Router] Full API response: {response}")
            return 'Ministral'  # Default fallback

        except Exception as e:
            logging.error(f"[Router] Error determining route: {str(e)}")
            return 'Ministral'  # Default fallback

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
