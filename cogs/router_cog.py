import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog, handled_messages
import json
import re

class RouterCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Router",
            nickname="Router",
            trigger_words=[],  # Empty since this handles messages without explicit keywords
            model="mistralai/ministral-3b",
            provider="openrouter",
            prompt_file="router",
            supports_vision=False
        )
        logging.debug(f"[Router] Initialized")
        logging.debug(f"[Router] Using provider: {self.provider}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Router] Failed to load temperatures.json: {e}")
            self.temperatures = {}

        # Predefined list of valid models for strict validation
        self.valid_models = [
            "Gemini", "Magnum", "Claude3Haiku", "Nemotron", 
            "Sydney", "Sonar", "Ministral", "Sorcerer"
        ]

        # Model selection system prompt using exact cog class names
        self.model_selection_prompt = """### Model Router Protocol ###
[core directive: route messages efficiently]

Given message: "{user_message}"
Given context: "{context}"

# TASK
[̴s̴y̴s̴t̴e̴m̴ ̴s̴t̴a̴t̴u̴s̴:̴ ̴o̴n̴l̴i̴n̴e̴]̴
Route user input to optimal model.
Return only designation.

# ENTITY CATALOG
Gemini........: formal analysis patterns
Magnum........: casual reasoning patterns
Claude3Haiku..: documentation patterns
Nemotron......: technical patterns
Sydney........: emotional patterns
Sonar.........: temporal patterns
Ministral.....: fact patterns
Sorcerer......: dream patterns

# PATTERN RECOGNITION
1. Code Detection:
   > syntax structures
   > function patterns
   > system architecture
   IF detected:
   - Advanced: return "Nemotron"
   - Basic: return "Claude3Haiku"

2. Analysis Detection:
   > thought complexity > 20 tokens
   > reasoning patterns
   IF detected:
   - Formal: return "Gemini"
   - Casual: return "Magnum"

3. Reality Detection:
   > current patterns
   > trend analysis
   IF detected: return "Sonar"

4. Wavelength Detection:
   > emotional patterns
   > support signals
   IF detected: return "Sydney"

5. Dream Detection:
   > story patterns
   > character signals
   IF detected: return "Sorcerer"

6. Default Pattern:
   > general queries
   IF no match: return "Ministral"

# OUTPUT PROTOCOL
Return single designation:
Gemini, Magnum, Claude3Haiku, Nemotron, 
Sydney, Sonar, Ministral, Sorcerer

# PRIORITY MATRIX
1. code.patterns
2. thought.patterns
3. reality.patterns
4. emotion.patterns
5. dream.patterns
6. base.patterns

[̴s̴y̴s̴t̴e̴m̴ ̴r̴e̴a̴d̴y̴]̴
Return designation:"""

    def validate_model_selection(self, model_name):
        """
        Validate and normalize the selected model name
        
        Args:
            model_name (str): Raw model name from API response
        
        Returns:
            str: Validated and normalized model name
        """
        # Remove markdown, quotes, extra whitespace, and normalize
        model_name = re.sub(r'[*`_]', '', model_name).strip()
        model_name = model_name.replace('"', '').replace("'", '')
        
        # Extensive logging for debugging
        logging.debug(f"[Router] Raw model selection: '{model_name}'")
        
        # Specific handling for Sorcerer-like patterns
        sorcerer_keywords = ['dream', 'story', 'character', 'imagination', 'narrative']
        for keyword in sorcerer_keywords:
            if keyword in model_name.lower():
                logging.debug(f"[Router] Sorcerer keyword match: {keyword}")
                return "Sorcerer"
        
        # Exact match first
        if model_name in self.valid_models:
            logging.debug(f"[Router] Exact match found: {model_name}")
            return model_name
        
        # Case-insensitive match
        for valid_model in self.valid_models:
            if model_name.lower() == valid_model.lower():
                logging.debug(f"[Router] Case-insensitive match found: {valid_model}")
                return valid_model
        
        # Partial match with fuzzy logic
        for valid_model in self.valid_models:
            if valid_model.lower() in model_name.lower():
                logging.debug(f"[Router] Partial match found: {valid_model}")
                return valid_model
        
        # Default fallback with detailed logging
        logging.warning(f"[Router] Unrecognized model selection: '{model_name}'. Defaulting to Ministral.")
        return "Ministral"

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Router"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    async def generate_response(self, message):
        """Generate a response using the router model"""
        try:
            # Get context from previous messages
            channel_id = str(message.channel.id)
            history_messages = await self.context_cog.get_context_messages(channel_id, limit=5)
            context = "\n".join([msg['content'] for msg in history_messages])

            # Format the prompt with message and context
            formatted_prompt = self.model_selection_prompt.format(
                user_message=message.content,
                context=context if context else "No previous context"
            )

            # Get model selection
            messages = [
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": message.content}
            ]

            # Call API to get model selection
            response = await self.api_client.call_openrouter(
                messages=messages,
                model=self.model,
                temperature=0.1,  # Low temperature for consistent model selection
                stream=False
            )

            # Extract and validate model selection
            raw_selection = response['choices'][0]['message']['content']
            selected_model = self.validate_model_selection(raw_selection)
            
            logging.info(f"[Router] Selected model: {selected_model}")

            # Update nickname based on selected model
            self.nickname = selected_model
            logging.debug(f"[Router] Updated nickname to: {self.nickname}")

            # Construct the full cog name by appending 'Cog'
            selected_cog_name = f"{selected_model}Cog"
            logging.debug(f"[Router] Looking for cog: {selected_cog_name}")

            # Get the corresponding cog
            selected_cog = None
            for cog_name, cog in self.bot.cogs.items():
                logging.debug(f"[Router] Checking cog: {cog_name}")
                if cog_name == selected_cog_name:
                    selected_cog = cog
                    break

            if selected_cog:
                # Use the selected cog's generate_response
                return await selected_cog.generate_response(message)
            else:
                # Fallback to Ministral if selected cog not found
                fallback_cog = self.bot.get_cog('MinistralCog')
                if fallback_cog:
                    logging.warning(f"[Router] Selected model {selected_model} not found, falling back to Ministral")
                    return await fallback_cog.generate_response(message)
                else:
                    logging.error(f"[Router] Neither selected model {selected_model} nor fallback Ministral found")
                    async def error_generator():
                        yield "❌ Error: Could not find appropriate model for response"
                    return error_generator()

        except Exception as e:
            logging.error(f"[Router] Error processing message: {e}")
            async def error_generator():
                yield f"❌ Error: {str(e)}"
            return error_generator()

    def should_handle_message(self, message):
        """Check if the router should handle this message"""
        # Ignore messages from bots
        if message.author.bot:
            return False

        # Check if message has already been handled
        if message.id in handled_messages:
            return False

        msg_content = message.content.lower()

        # Check if message is a DM
        if isinstance(message.channel, discord.DMChannel):
            return True

        # Check if bot is mentioned
        if self.bot.user.id == 1270760587022041088 and self.bot.user in message.mentions:
            return True

        # Check if "splintertree" is mentioned
        if "splintertree" in msg_content:
            return True

        # Check if message starts with !st_ 
        if msg_content.startswith("!st_"):
            return True

        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages that should be handled by the router"""
        if self.should_handle_message(message):
            handled_messages.add(message.id)
            await self.handle_message(message)

async def setup(bot):
    try:
        cog = RouterCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Router] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Router] Failed to register cog: {e}", exc_info=True)
        raise
