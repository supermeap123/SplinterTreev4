import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog, handled_messages
import json

class FreeRouterCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="FreeRouter",
            nickname="FreeRouter",
            trigger_words=["openrouter", "freerouter"],  # Added both keywords
            model="openpipe:FreeRouter-v1-162",
            provider="openpipe",
            prompt_file="freerouter",
            supports_vision=False
        )
        logging.debug(f"[FreeRouter] Initialized")
        logging.debug(f"[FreeRouter] Using provider: {self.provider}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[FreeRouter] Failed to load temperatures.json: {e}")
            self.temperatures = {}

        # Model selection system prompt
        self.model_selection_prompt = """### FreeRouter Model Selection Prompt ###
        
Given message: "{user_message}"
Given context: "{context}"

# TASK
You are FreeRouter, an AI model that selects the most appropriate AI model based on message content.
Return ONLY the exact model ID without explanation or additional text.

# AVAILABLE MODELS AND USE CASES
- Gemini: Complex analytical reasoning with formal tone  
- Magnum: Complex reasoning with casual/conversational tone
- Claude3Haiku: Basic coding questions and programming help
- Nemotron: Complex coding and technical programming
- Sydney: Emotional support and empathy
- Sonar: Internet trends and current events
- Ministral: General factual queries
- Sorcerer: Advanced RP and storytelling

# ANALYSIS STEPS
1. Check for code indicators:
   - Code blocks (```)
   - Programming terms (function, code, api, database)
   IF found:
     IF complex/advanced -> Nemotron
     IF basic/simple -> Claude3Haiku

2. Check for complex reasoning:
   - Message length > 20 words
   - Analysis terms (analyze, evaluate, compare)
   IF found:
     IF formal/academic tone -> Gemini
     IF casual/conversational -> Magnum

3. Check for trends/events:
   - News/current event terms
   - "What's happening"
   - Trends/popularity
   IF found -> Sonar

4. Check for emotional content:
   - Feeling words
   - Support seeking
   - Personal issues
   IF found -> Sydney

5. Check for RP and storytelling indicators:
   - Story/narrative elements
   - Character interactions
   - World-building details
   IF found -> Sorcerer

6. If no other match -> Ministral

# OUTPUT FORMAT
Return exactly one of: Gemini, Magnum, Claude3Haiku, Nemotron, Sydney, Sonar, Ministral, Sorcerer

# PRIORITY ORDER (IF MULTIPLE MATCH)
1. Code (Nemotron/Claude3Haiku)
2. Complex reasoning (Gemini/Magnum)
3. Trends (Sonar)
4. Emotional (Sydney)
5. RP and storytelling (Sorcerer)
6. General (Ministral)

Return model ID:"""

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "FreeRouter"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    async def generate_response(self, message):
        """
        Generate a response using the selected model.
        """
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

            selected_model = response['choices'][0]['message']['content'].strip()
            # Remove any quotes if present
            selected_model = selected_model.replace('"', '').replace("'", '')
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
