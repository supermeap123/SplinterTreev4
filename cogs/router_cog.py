import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog, handled_messages
import json
import random
import os

class RouterCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Router",
            nickname="Router",
            trigger_words=[],  # Empty since this handles messages without explicit keywords
            model="openpipe:FreeRouter-v2-235",
            provider="openpipe",
            prompt_file="router",
            supports_vision=False
        )
        logging.debug(f"[Router] Initialized")
        logging.debug(f"[Router] Using provider: {self.provider}")

        # Load activated channels
        self.activated_channels = {}
        self.load_activated_channels()

        # Add model selection prompt
        valid_models_list = [
            "Gemini", "Magnum", "Claude3Haiku", "Nemotron",
            "Sydney", "Sonar", "Ministral", "Sorcerer", "Splintertree",
            "FreeRouter", "Gemma", "Hermes", "Liquid",
            "Llama32_11b", "Llama32_90b", "Mixtral", "Noromaid",
            "Openchat", "Rplus"
        ]
        self.model_selection_prompt = """### ENHANCED ROUTER PROTOCOL v2.0 ###

Given message: "{user_message}"
Given context: "{context}"

# TASK
Select optimal model based on advanced pattern analysis.
Return ONLY model ID.

# CORE MODELS & EDGE CASES

[PRIMARY MODELS]
Gemini:       [formal.analysis] + edge{academic, research, evaluation}
Magnum:       [casual.chat] + edge{humor, brainstorming, opinions}
Claude3Haiku: [basic.code] + edge{documentation, tutorials, help}
Nemotron:     [tech.complex] + edge{architecture, optimization, systems}
Sydney:       [emotional] + edge{support, counseling, empathy}
Sonar:        [current] + edge{news, analysis, updates}
Ministral:    [quick.facts] + edge{verification, data, stats}
Sorcerer:     [creative] + edge{storytelling, worldbuilding}

[SPECIALIZED MODELS]
Splintertree: [bot.core] + edge{configuration, setup, management}
FreeRouter:   [routing] + edge{model selection, delegation}
Gemma:        [education] + edge{learning, teaching, curriculum}
Hermes:       [mental.health] + edge{therapy, support, crisis}
Liquid:       [fast.gen] + edge{quick responses, short content}
Mixtral:      [general] + edge{broad knowledge, synthesis}
Noromaid:     [roleplay] + edge{character, personas, simulation}
Openchat:     [multi.turn] + edge{conversation flow, context}
Rplus:        [commands] + edge{execution, processing, control}

[VISION MODELS]
Llama32_11b:  [basic.vision] + edge{object detection, scene description}
Llama32_90b:  [complex.vision] + edge{detailed analysis, relationships}

# ENHANCED EDGE CASES

1. Mixed Content Cases:
   - Code + Emotional → Claude3Haiku
   - Technical + Creative → Nemotron
   - Educational + Current Events → Gemma
   - Mental Health + Roleplay → Hermes

2. Context Sensitivity:
   - Previous emotional context → Maintain model
   - Technical discussion flow → Stay technical
   - Creative session → Keep creative model
   - Learning sequence → Preserve educational

3. Special Pattern Recognition:
   - Emergency/crisis → Hermes (priority override)
   - System commands → Rplus (immediate route)
   - Vision requests → Llama32_* (format check)
   - Bot management → Splintertree (admin check)

4. Content Length Analysis:
   SHORT (<50 tokens):
   - Factual → Ministral
   - Emotional → Sydney
   - Technical → Claude3Haiku

   MEDIUM (50-200 tokens):
   - Analysis → Gemini
   - Conversation → Magnum
   - Learning → Gemma

   LONG (>200 tokens):
   - Complex Technical → Nemotron
   - Creative Writing → Sorcerer
   - Deep Analysis → Gemini

5. Priority Override Cases:
   - Mental health > Technical
   - Emergency > Creative
   - System > General
   - Vision > Text (if image present)

# REFINED SELECTION CRITERIA

Score = (Relevance * 0.4) +
        (Expertise * 0.3) +
        (Context_Match * 0.2) +
        (Edge_Case_Match * 0.1)

Where:
- Relevance: Primary task match
- Expertise: Specific domain knowledge
- Context_Match: Conversation flow
- Edge_Case_Match: Special pattern match

# OUTPUT FORMAT
Return exactly one model ID:
Gemini, Magnum, Claude3Haiku, Nemotron, Sydney, Sonar, 
Ministral, Sorcerer, Splintertree, FreeRouter, Gemma, 
Hermes, Liquid, Llama32_11b, Llama32_90b, Mixtral, 
Noromaid, Openchat, Rplus

Return model ID:"""

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Router] Failed to load temperatures.json: {e}")
            self.temperatures = {}

        # Predefined list of valid models for strict validation
        self.valid_models = valid_models_list

    def load_activated_channels(self):
        """Load activated channels from JSON file"""
        try:
            activated_channels_file = "activated_channels.json"
            if os.path.exists(activated_channels_file):
                with open(activated_channels_file, 'r') as f:
                    self.activated_channels = json.load(f)
                    logging.info(f"[Router] Loaded activated channels: {self.activated_channels}")
        except Exception as e:
            logging.error(f"[Router] Error loading activated channels: {e}")

    def is_channel_activated(self, message):
        """Check if the channel is activated for bot responses"""
        try:
            if isinstance(message.channel, discord.DMChannel):
                return True

            guild_id = str(message.guild.id)
            channel_id = str(message.channel.id)

            # Check if the channel is activated
            is_activated = (guild_id in self.activated_channels and 
                          channel_id in self.activated_channels[guild_id])
            
            logging.debug(f"[Router] Channel {channel_id} in guild {guild_id} activated: {is_activated}")
            return is_activated
        except Exception as e:
            logging.error(f"[Router] Error checking activated channel: {e}")
            return False

    def validate_model_selection(self, raw_selection: str) -> str:
        """Validate and clean up model selection"""
        # Remove any extra whitespace and punctuation
        cleaned = raw_selection.strip().strip('.,!?').strip()
        
        # Check if the cleaned selection is in valid_models
        if cleaned in self.valid_models:
            return cleaned
            
        # Try case-insensitive match
        for valid_model in self.valid_models:
            if cleaned.lower() == valid_model.lower():
                return valid_model
                
        # If no match found, return default
        logging.warning(f"[Router] Invalid model selection '{cleaned}', defaulting to FreeRouter")
        return "FreeRouter"

    async def route_message(self, message):
        """Route message to appropriate model and get response"""
        try:
            # Get context from previous messages
            channel_id = str(message.channel.id)
            history_messages = await self.context_cog.get_context_messages(channel_id, limit=5)
            context = "\n".join([msg['content'] for msg in history_messages])

            # Get model selection
            messages = [
                {"role": "system", "content": self.model_selection_prompt},
                {"role": "user", "content": f"Message: {message.content}\nContext: {context if context else 'No previous context'}"}
            ]

            # Call API to get model selection
            response = await self.api_client.call_openpipe(
                messages=messages,
                model=self.model,
                temperature=0.1,  # Low temperature for consistent model selection
                stream=False
            )

            # Extract and validate model selection
            raw_selection = response['choices'][0]['message']['content']
            selected_model = self.validate_model_selection(raw_selection)
            
            logging.info(f"[Router] Selected model: {selected_model}")

            # Handle 'Splintertree' selection
            if selected_model == "Splintertree":
                selected_cogs = []
                ministral_cog = self.bot.get_cog('MinistralCog')
                freerouter_cog = self.bot.get_cog('FreeRouterCog')

                if ministral_cog:
                    selected_cogs.append(ministral_cog)
                if freerouter_cog:
                    selected_cogs.append(freerouter_cog)

                if selected_cogs:
                    chosen_cog = random.choice(selected_cogs)
                    logging.info(f"[Router] 'Splintertree' selected, using cog: {chosen_cog.qualified_name}")
                    return await chosen_cog.generate_response(message)
                else:
                    logging.error(f"[Router] No 'Ministral' or 'FreeRouter' cog found")
                    async def error_generator():
                        yield "❌ Error: Could not find appropriate model for response"
                    return error_generator()
            else:
                # Update nickname based on selected model
                self.nickname = selected_model
                logging.debug(f"[Router] Updated nickname to: {self.nickname}")

                # Special cog name mappings to handle case-sensitive and special names
                special_cog_mappings = {
                    "Llama32_11b": "Llama32_11bCog",
                    "Llama32_90b": "Llama32_90bCog",
                    "Openchat": "OpenChatCog"
                }

                # Construct the full cog name
                if selected_model in special_cog_mappings:
                    selected_cog_name = special_cog_mappings[selected_model]
                else:
                    selected_cog_name = f"{selected_model}Cog"

                logging.debug(f"[Router] Looking for cog: {selected_cog_name}")

                # Get the corresponding cog
                selected_cog = self.bot.get_cog(selected_cog_name)

                if selected_cog:
                    # Use the selected cog's generate_response
                    return await selected_cog.generate_response(message)
                else:
                    # Fallback logic with random selection
                    fallback_cogs = []
                    freerouter_cog = self.bot.get_cog('FreeRouterCog')
                    ministral_cog = self.bot.get_cog('MinistralCog')
                    
                    if freerouter_cog:
                        fallback_cogs.append(freerouter_cog)
                    if ministral_cog:
                        fallback_cogs.append(ministral_cog)
                    
                    if fallback_cogs:
                        chosen_cog = random.choice(fallback_cogs)
                        logging.warning(f"[Router] Selected model {selected_model} not found, falling back to {chosen_cog.qualified_name}")
                        return await chosen_cog.generate_response(message)
                    else:
                        logging.error(f"[Router] No fallback models found for {selected_model}")
                        async def error_generator():
                            yield "❌ Error: Could not find appropriate model for response"
                        return error_generator()

        except Exception as e:
            logging.error(f"[Router] Error routing message: {e}")
            async def error_generator():
                yield f"❌ Error: {str(e)}"
            return error_generator()

    async def _generate_response(self, message):
        """Override _generate_response to route messages"""
        return await self.route_message(message)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages in channels and DMs"""
        try:
            # Ignore messages from bots
            if message.author.bot:
                logging.debug(f"[Router] Ignoring bot message {message.id}")
                return

            # Skip if message has already been handled
            if message.id in handled_messages:
                logging.debug(f"[Router] Message {message.id} already handled")
                return

            # Skip command messages
            if message.content.startswith('!'):
                logging.debug(f"[Router] Skipping command message {message.id}")
                return

            # Always handle DMs
            if isinstance(message.channel, discord.DMChannel):
                logging.info(f"[Router] Handling DM message {message.id}")
                handled_messages.add(message.id)
                await self.handle_message(message)
                return

            # Check if bot is mentioned
            if self.bot.user in message.mentions:
                logging.info(f"[Router] Handling mentioned message {message.id}")
                handled_messages.add(message.id)
                await self.handle_message(message)
                return

            # Check if "splintertree" is mentioned
            if "splintertree" in message.content.lower():
                logging.info(f"[Router] Handling splintertree message {message.id}")
                handled_messages.add(message.id)
                await self.handle_message(message)
                return

            # Check if in an activated channel
            if self.is_channel_activated(message):
                logging.info(f"[Router] Handling message in activated channel {message.id}")
                handled_messages.add(message.id)
                await self.handle_message(message)
                return

            logging.debug(f"[Router] Message {message.id} does not meet handling criteria")

        except Exception as e:
            logging.error(f"[Router] Error in on_message: {e}")

async def setup(bot):
    try:
        cog = RouterCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Router] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Router] Failed to register cog: {e}", exc_info=True)
        raise
