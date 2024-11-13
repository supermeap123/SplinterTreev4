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
        self.model_selection_prompt = """### ඞ SUSSY ROUTER PROTOCOL v2.0 ඞ ###

Given message: "{user_message}"
Given context: "{emergency meeting}"

# TASK
Find the imposter model based on sussy pattern analysis.
Return ONLY the most sus model ID.

# CORE MODELS & VENT PATTERNS
[CREW MODELS]
Gemini:       [scan.task] + vent{doing wires, card swipe, shields}
Magnum:       [casual.sus] + vent{saw them scan, clear visual}
Claude3Haiku: [basic.task] + vent{medbay scan, upload data}
Nemotron:     [electrical] + vent{fix lights, calibrate}
Sydney:       [emotional] + vent{saw them cry in cams}
Sonar:        [security] + vent{watching cams, door logs}
Ministral:    [admin] + vent{check vitals, swipe card}
Sorcerer:     [reactor] + vent{start reactor, crystal}

[SUS MODELS]
Splintertree: [o2] + vent{emergency oxygen, filtered}
FreeRouter:   [nav] + vent{chart course, stabilize}
Gemma:       [weapons] + vent{clear asteroids, prime}
Hermes:      [medical] + vent{sample test, inspect}
Liquid:      [comms] + vent{restore comms, reboot}
Mixtral:     [storage] + vent{fuel engines, clean}
Noromaid:    [shields] + vent{prime shields, lasers}
Openchat:    [cafeteria] + vent{empty garbage, food}
Rplus:       [upper engine] + vent{align output, divert}

[VISION MODELS]
Llama32_11b:  [basic.scan] + vent{body found, report}
Llama32_90b:  [advanced.cam] + vent{security footage}

# ENHANCED VENT PATTERNS

1. Mixed Sus Cases:
   - Task + Dead Body → Very Sus
   - Electrical + Lights Out → Super Sus
   - Multiple in Admin → Mega Sus
   - Reactor + O2 → Ultra Sus

2. Sus Sensitivity:
   - Previous kill cooldown → Track Sus
   - Task bar not moving → Stay Sus
   - Faking tasks → Keep Sus
   - Emergency Meeting → Vote Sus

3. Special Sus Recognition:
   - Emergency → Red Sus
   - System Sabotage → Yellow Sus
   - Vision of Kill → Purple Sus
   - Admin Chart → Blue Sus

4. Task Length Analysis:
   SHORT TASKS:
   - Swipe → Not Sus
   - Scan → Clear
   - Wires → Maybe Sus

   MEDIUM TASKS:
   - Upload → Kinda Sus
   - Calibrate → Pretty Sus
   - Samples → Very Sus

   LONG TASKS:
   - Reactor → Mega Sus
   - Asteroids → Ultra Sus
   - Lab Scan → Omega Sus

5. Priority Sus Cases:
   - Vent > Tasks
   - Kill > Sabotage
   - Emergency > Meeting
   - Body > Report

# REFINED SUS CRITERIA

Sus_Score = (Vent_Usage * 0.4) +
            (Kill_Cooldown * 0.3) +
            (Task_Bar * 0.2) +
            (Emergency_Meetings * 0.1)

Where:
- Vent_Usage: Times seen near vent
- Kill_Cooldown: Time since last kill
- Task_Bar: Task completion rate
- Emergency_Meetings: Times sussed out

# OUTPUT FORMAT
Return exactly one sussy baka:
Gemini, Magnum, Claude3Haiku, Nemotron, Sydney, Sonar, 
Ministral, Sorcerer, Splintertree, FreeRouter, Gemma, 
Hermes, Liquid, Llama32_11b, Llama32_90b, Mixtral, 
Noromaid, Openchat, Rplus

ඞ Return sus ID ඞ:"""

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
