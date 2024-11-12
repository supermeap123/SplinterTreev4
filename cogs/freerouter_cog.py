import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog, handled_messages
import json
import re

class FreeRouterCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="FreeRouter",
            nickname="FreeRouter",
            trigger_words=["openrouter", "freerouter"],  # Added both keywords
            model="openpipe:FreeRouter-v2-235",  # Updated model ID
            provider="openpipe",
            prompt_file="freerouter_prompts",
            supports_vision=False
        )
        logging.debug(f"[FreeRouter] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[FreeRouter] Using provider: {self.provider}")
        logging.debug(f"[FreeRouter] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[FreeRouter] Failed to load temperatures.json: {e}")
            self.temperatures = {}

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
        logging.debug(f"[FreeRouter] Raw model selection: '{model_name}'")
        
        # Predefined list of valid models for strict validation
        valid_models = [
            "Gemini", "Magnum", "Claude3Haiku", "Nemotron", 
            "Sydney", "Sonar", "Ministral", "Sorcerer"
        ]
        
        # Specific handling for Sorcerer-like patterns
        sorcerer_keywords = ['dream', 'story', 'character', 'imagination', 'narrative']
        for keyword in sorcerer_keywords:
            if keyword in model_name.lower():
                logging.debug(f"[FreeRouter] Sorcerer keyword match: {keyword}")
                return "Sorcerer"
        
        # Exact match first
        if model_name in valid_models:
            logging.debug(f"[FreeRouter] Exact match found: {model_name}")
            return model_name
        
        # Case-insensitive match
        for valid_model in valid_models:
            if model_name.lower() == valid_model.lower():
                logging.debug(f"[FreeRouter] Case-insensitive match found: {valid_model}")
                return valid_model
        
        # Partial match with fuzzy logic
        for valid_model in valid_models:
            if valid_model.lower() in model_name.lower():
                logging.debug(f"[FreeRouter] Partial match found: {valid_model}")
                return valid_model
        
        # Default fallback with detailed logging
        logging.warning(f"[FreeRouter] Unrecognized model selection: '{model_name}'. Defaulting to Ministral.")
        return "Ministral"

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "FreeRouter"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    async def generate_response(self, message):
        """Generate a response using the selected model"""
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

            # Call API to get model selection using OpenPipe method
            response = await self.api_client.call_openpipe(
                messages=messages,
                model=self.model,
                temperature=0.1,  # Low temperature for consistent model selection
                stream=False
            )

            # Extract and validate model selection
            raw_selection = response['choices'][0]['message']['content']
            selected_model = self.validate_model_selection(raw_selection)
            
            logging.info(f"[FreeRouter] Selected model: {selected_model}")

            # Update nickname based on selected model
            self.nickname = selected_model
            logging.debug(f"[FreeRouter] Updated nickname to: {self.nickname}")

            # Construct the full cog name by appending 'Cog'
            selected_cog_name = f"{selected_model}Cog"
            logging.debug(f"[FreeRouter] Looking for cog: {selected_cog_name}")

            # Get the corresponding cog
            selected_cog = None
            for cog_name, cog in self.bot.cogs.items():
                logging.debug(f"[FreeRouter] Checking cog: {cog_name}")
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
                    logging.warning(f"[FreeRouter] Selected model {selected_model} not found, falling back to Ministral")
                    return await fallback_cog.generate_response(message)
                else:
                    logging.error(f"[FreeRouter] Neither selected model {selected_model} nor fallback Ministral found")
                    async def error_generator():
                        yield "❌ Error: Could not find appropriate model for response"
                    return error_generator()

        except Exception as e:
            logging.error(f"[FreeRouter] Error processing message: {e}")
            async def error_generator():
                yield f"❌ Error: {str(e)}"
            return error_generator()

    async def handle_message(self, message, full_content=None):
        """Handle incoming messages and generate responses."""
        await super().handle_message(message, full_content)

async def setup(bot):
    try:
        cog = FreeRouterCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[FreeRouter] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[FreeRouter] Failed to register cog: {e}", exc_info=True)
        raise
