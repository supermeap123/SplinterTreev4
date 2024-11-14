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
            r'\b(use|switch to|try|with)\s+(gemini|magnum|sonar|sydney|goliath|pixtral|mixtral|claude3haiku|inferor|nemotron|noromaid|rplus|router|llama32_11b|llama32_90b|openchat|dolphin|gemma|ministral|liquid|hermes|unslopnemo)\b',
            r'\b(gemini|magnum|sonar|sydney|goliath|pixtral|mixtral|claude3haiku|inferor|nemotron|noromaid|rplus|router|llama32_11b|llama32_90b|openchat|dolphin|gemma|ministral|liquid|hermes|unslopnemo)\s+(please|now|instead)\b',
            r'^(gemini|magnum|sonar|sydney|goliath|pixtral|mixtral|claude3haiku|inferor|nemotron|noromaid|rplus|router|llama32_11b|llama32_90b|openchat|dolphin|gemma|ministral|liquid|hermes|unslopnemo)[,:]\s',
            r'\b(gemini|magnum|sonar|sydney|goliath|pixtral|mixtral|claude3haiku|inferor|nemotron|noromaid|rplus|router|llama32_11b|llama32_90b|openchat|dolphin|gemma|ministral|liquid|hermes|unslopnemo)\b'  # Added to catch standalone model names
         ]

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
            'Ministeral': 'MinistralCog',
            'Liquid': 'LiquidCog',
            'Hermes': 'HermesCog',
            'UnslopNemo': 'UnslopNemoCog'  # Added UnslopNemo
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
                        str(message.channel.id) if message.channel else None,
                        limit=5,
                        exclude_message_id=str(message.id)
                    )
                    context = "\n".join([msg['content'] for msg in history])
                    logging.debug(f"[Router] Got context: {context[:200]}...")
                except Exception as e:
                    logging.error(f"[Router] Error getting context: {str(e)}")

            # Format the routing prompt
            routing_prompt = f"""### UNIFIED PRODUCTION ROUTER v8.0 ###
Message: "{message.content}"
Context: "{context}"

[MODEL PATHS & STRENGTHS]

ANALYTICAL PATHS
├─ Gemini
│  ├─ Strengths: Formal analysis, multilingual, research
│  ├─ Best for: Academic writing, detailed explanations
│  ├─ Context: Previous analysis, formal discussions
│  └─ Token sweet spot: >200
│
└─ Magnum
   ├─ Strengths: Casual analysis, creative expansion
   ├─ Best for: Friendly explanations, brainstorming
   ├─ Context: Informal discussion, idea generation
   └─ Token sweet spot: 100-500

REAL-TIME INFORMATION PATH
└─ Sonar
   ├─ Strengths: Current events, trends, updates
   ├─ Best for: Time-sensitive info, recent changes
   ├─ Context: Modern queries, updates needed
   └─ Priority override: Latest info needs

TECHNICAL PATHS
├─ Nemotron
│  ├─ Strengths: Complex code, system design
│  ├─ Best for: Advanced technical, optimization
│  ├─ Context: Development, architecture
│  └─ Token sweet spot: >300
│
└─ Claude3Haiku
   ├─ Strengths: Basic code, documentation
   ├─ Best for: Quick help, examples
   ├─ Context: Learning, basics
   └─ Token sweet spot: <200

ROLEPLAY PATHS - EXTENDED
├─ Epic Scale (Magnum/Noromaid)
│  ├─ Token range: >1000
│  ├─ Scenarios: Campaigns, wars, politics
│  ├─ Context: Multi-character, complex plots
│  └─ Triggers: "saga", "campaign", "epic"
│
├─ Complex Scenes (Noromaid/UnslopNemo)
│  ├─ Token range: 500-1000
│  ├─ Scenarios: Character development, relationships
│  ├─ Context: Deep interaction, emotional
│  └─ Triggers: "scene", "develop", "unfolds"
│
├─ Medium Interactions (UnslopNemo/Mixtral)
│  ├─ Token range: 200-500
│  ├─ Scenarios: Group scenes, dialogue
│  ├─ Context: Social interaction, exploration
│  └─ Triggers: "interact", "explore", "discuss"
│
└─ Quick Actions (Liquid)
   ├─ Token range: <200
   ├─ Scenarios: Combat turns, quick responses
   ├─ Context: Immediate actions, reactions
   └─ Triggers: "quickly", "reacts", "responds"

EMOTIONAL SUPPORT PATHS
├─ Sydney
│  ├─ Strengths: Empathy, emotional intelligence
│  ├─ Best for: Personal support, relationships
│  ├─ Context: Emotional discussions
│  └─ Token sweet spot: 100-400
│
└─ Hermes
   ├─ Strengths: Mental health, crisis support
   ├─ Best for: Sensitive topics, emergency
   ├─ Context: Support needs
   └─ Priority override: Crisis detection

[SEMANTIC CLOUDS & FUZZY MATCHING]

RP COMPLEXITY TRIGGERS
├─ Epic Scale
│  ├─ Primary: [saga, campaign, epic, chronicle, legend]
│  ├─ Action: [conquer, rule, lead, command, govern]
│  ├─ Scope: [kingdom, empire, world, realm, dynasty]
│  ├─ Politics: [intrigue, diplomacy, alliance, treaty]
│  └─ Pattern: (?=.*\\b(epic|saga)\\b)(?=.*\\b(world|kingdom)\\b)
│
├─ Complex Scene
│  ├─ Development: [growth, evolution, change, transform]
│  ├─ Character: [personality, background, history, depth]
│  ├─ Emotion: [feeling, sentiment, mood, atmosphere]
│  └─ Pattern: (?=.*\\b(character|scene)\\b)(?=.*\\b(deep|complex)\\b)
│
├─ Medium Scene
│  ├─ Action: [interact, explore, investigate, discover]
│  ├─ Social: [talk, discuss, meet, gather, convene]
│  ├─ Movement: [travel, journey, walk, ride, traverse]
│  └─ Pattern: (?=.*\\b(explore|interact)\\b)(?=.*\\b(group|party)\\b)
│
└─ Quick Action
   ├─ Combat: [attack, defend, dodge, strike, parry]
   ├─ Movement: [jump, run, dash, leap, sprint]
   ├─ Response: [react, answer, reply, respond]
   └─ Pattern: (?=.*\\b(quick|fast)\\b)(?=.*\\b(action|move)\\b)

INFORMATION RECENCY TRIGGERS
├─ Time Indicators
│  ├─ Current: [now, present, ongoing, current, active]
│  ├─ Recent: [latest, new, fresh, updated, modern]
│  ├─ Trending: [popular, viral, hot, buzzing]
│  └─ Pattern: (?=.*\\b(current|latest)\\b)|(?=.*\\b(now|trending)\\b)
│
└─ Update Needs
   ├─ Status: [state, condition, situation, status]
   ├─ Changes: [update, revision, modification, change]
   ├─ News: [announcement, report, release, update]
   └─ Pattern: (?=.*\\b(update|change)\\b)(?=.*\\b(status|news)\\b)

TECHNICAL COMPLEXITY TRIGGERS
├─ Advanced
│  ├─ Code: [optimize, architect, design, implement]
│  ├─ System: [infrastructure, framework, platform]
│  ├─ Scale: [enterprise, distributed, scalable]
│  └─ Pattern: (?=.*\\b(complex|advanced)\\b)(?=.*\\b(system|code)\\b)
│
└─ Basic
   ├─ Help: [assist, guide, explain, show]
   ├─ Learn: [understand, practice, begin, start]
   ├─ Basic: [simple, fundamental, elementary]
   └─ Pattern: (?=.*\\b(help|learn)\\b)(?=.*\\b(basic|simple)\\b)

[CONTEXT WEIGHTING SYSTEM]

TOKEN-BASED WEIGHTS
├─ Micro (<50 tokens): 0.5x
├─ Small (50-200): 1.0x
├─ Medium (200-500): 1.5x
├─ Large (500-1000): 2.0x
└─ Epic (>1000): 2.5x

CONTEXT CONTINUITY
├─ Previous model used: 1.3x
├─ Theme consistency: 1.2x
├─ Character continuity: 1.4x
└─ Scene continuity: 1.5x

TIME SENSITIVITY
├─ Emergency: 3.0x
├─ Current events: 2.5x
├─ Recent changes: 2.0x
└─ General query: 1.0x

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

3. COMPLEXITY OVERRIDES
   ├─ Technical complexity → Nemotron
   ├─ RP epic scale → Magnum/Noromaid
   ├─ Deep emotion → Sydney
   └─ Priority: High

4. LENGTH OVERRIDES
   ├─ >1000 tokens → Magnum/Noromaid
   ├─ 500-1000 → Noromaid/UnslopNemo
   ├─ 200-500 → UnslopNemo/Mixtral
   └─ <200 → Liquid/Ministral

[FUZZY LOGIC SCORING SYSTEM]

MATCH SCORING
├─ Exact Match: 1.0
├─ Stem Match: 0.9 (analyze/analyzing)
├─ Synonym Match: 0.8 (quick/fast)
├─ Related Match: 0.6 (story/tale)
├─ Context Match: 0.4 (implied meaning)
└─ Minimum Threshold: 0.3

COMPOSITE SCORE CALCULATION
Score = (KeywordMatch * 0.3) +
        (ContextMatch * 0.25) +
        (LengthMatch * 0.2) +
        (TimeMatch * 0.15) +
        (PatternMatch * 0.1)

SCORE ADJUSTMENTS
├─ Emergency Multiplier: 3.0x
├─ Current Info Need: 2.5x
├─ Context Continuity: 1.5x
├─ Scene Complexity: 1.3x
└─ Basic Query: 1.0x

[IMPLEMENTATION RULES]

PATTERN RECOGNITION
1. Check for emergency/crisis first
2. Evaluate time sensitivity
3. Analyze message length
4. Detect context patterns
5. Apply fuzzy matching
6. Calculate composite score
7. Apply adjustments
8. Select highest score above threshold

LENGTH DETECTION
├─ Token Count Ranges
│  ├─ Micro: <50 tokens
│  ├─ Small: 50-200 tokens
│  ├─ Medium: 200-500 tokens
│  ├─ Large: 500-1000 tokens
│  └─ Epic: >1000 tokens
│
└─ Model Preferences
   ├─ Micro → Liquid/Ministral
   ├─ Small → Claude3Haiku/Mixtral
   ├─ Medium → UnslopNemo/Mixtral
   ├─ Large → Noromaid/Magnum
   └─ Epic → Magnum/Noromaid

CONTEXT HANDLING
1. Store previous model used
2. Track conversation theme
3. Monitor scene continuity
4. Check character persistence
5. Evaluate topic shifts
6. Maintain narrative flow
7. Consider time gaps
8. Preserve RP consistency

[EXAMPLE PATTERNS]

RP SCENARIOS
├─ Epic Campaign
│  Input: "The kingdom faces a growing threat from the ancient dragons..."
│  Length: >1000 tokens
│  Context: World-building, politics
│  Result: Magnum
│
├─ Character Development
│  Input: "As they sit by the campfire, Clara reflects on her journey..."
│  Length: 500-1000 tokens
│  Context: Personal growth, reflection
│  Result: Noromaid
│
├─ Group Interaction
│  Input: "The party enters the tavern, looking for information..."
│  Length: 200-500 tokens
│  Context: Social scene, exploration
│  Result: UnslopNemo
│
└─ Quick Combat
   Input: "Clara dodges the incoming arrow and draws her sword..."
   Length: <200 tokens
   Context: Action scene, immediate
   Result: Liquid

CURRENT INFO QUERIES
├─ News Request
│  Input: "What's happening with the latest tech regulations?"
│  Pattern: Current events + specific topic
│  Result: Sonar
│
└─ Update Check
   Input: "Which version of Python is current for ML?"
   Pattern: Status check + technical
   Result: Sonar

TECHNICAL SCENARIOS
├─ Complex System
│  Input: "Design a distributed caching system for..."
│  Pattern: Advanced + technical
│  Result: Nemotron
│
└─ Basic Help
   Input: "How do I write a for loop in Python?"
   Pattern: Basic + learning
   Result: Claude3Haiku

[FINAL OUTPUT RULES]

1. Return ONLY the model ID
2. No explanation
3. No context
4. No reasoning
5. Exactly one of:
   Gemini, Magnum, Sonar, Sydney, Goliath, Pixtral, 
   Mixtral, Claude3Haiku, Inferor, Nemotron, Noromaid, 
   Rplus, Router, Llama32_11b, Llama32_90b, OpenChat, 
   Dolphin, Gemma, Ministral, Liquid, Hermes, UnslopNemo

Model ID:"""

            # Add image presence info
            has_image = self.has_image_attachments(message)
            if has_image:
                routing_prompt = f"Note: Message contains image attachments.\n\n{routing_prompt}"
                logging.debug("[Router] Message contains image attachments")

            # Call OpenRouter API for inference
            messages = [
                {"role": "system", "content": "You are a message routing assistant. Return only the model ID."},
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
