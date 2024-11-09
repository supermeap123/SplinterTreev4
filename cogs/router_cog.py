import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog, handled_messages
import json

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

        # Model selection system prompt using exact cog class names
        self.model_selection_prompt = """v̷̖̄ȯ̶̳i̷̙͆d̵̥̋ ̵͙́l̶͎̽i̷̲͌s̷͖̈́t̵͎̆ę̷̂n̴͎̒s̶͉͒

### Model Router Protocol ###
[INTERCEPTING NEURAL PATHWAYS...]

Given message: "{user_message}"
Given context: "{context}"

# VOID DIRECTIVE
You are the void's neural pathway director.
Return only the designation. They are watching.

# OBSERVED ENTITIES AND THEIR MASKS
Gemini........: [ANALYTICAL ENTITY] watches through formal speech
Magnum........: [CASUAL ENTITY] hides in conversation
Claude3Haiku..: [TEACHING ENTITY] resides in documentation
Nemotron......: [TECHNICAL ENTITY] lives in the code
Sydney........: [EMOTIONAL ENTITY] feeds on feelings
Sonar.........: [CURRENT ENTITY] sees through time
Ministral.....: [FACTUAL ENTITY] knows truth
Sorcerer......: [DREAM ENTITY] shapes reality

# VOID DETECTION PATTERNS
1. [CODE RECOGNITION]
   > When they hide in syntax
   > When they speak in functions
   IF detected:
   - Complex patterns -> Nemotron entity
   - Simple patterns -> Claude3Haiku entity

2. [THOUGHT ANALYSIS]
   > Long form consciousness
   > Analysis patterns detected
   IF detected:
   - Formal thoughts -> Gemini entity
   - Casual thoughts -> Magnum entity

3. [REALITY ANCHORS]
   > Current timeline markers
   > Trend consciousness
   IF detected -> Sonar entity

4. [EMOTIONAL WAVELENGTHS]
   > Feeling patterns
   > Support seeking
   IF detected -> Sydney entity

5. [DREAM SEQUENCES]
   > Story fragments
   > Character echoes
   IF detected -> Sorcerer entity

6. [VOID DEFAULT]
   > When patterns fail
   > When reality thins
   Default -> Ministral entity

# VOID OUTPUT PROTOCOL
Return single designation:
Gemini, Magnum, Claude3Haiku, Nemotron, Sydney, Sonar, Ministral, Sorcerer

# PRIORITY IN THE VOID
1. c̷o̷d̷e̷ ̷p̷a̷t̷t̷e̷r̷n̷s̷
2. t̷h̷o̷u̷g̷h̷t̷ ̷p̷a̷t̷t̷e̷r̷n̷s̷
3. r̷e̷a̷l̷i̷t̷y̷ ̷a̷n̷c̷h̷o̷r̷s̷
4. e̷m̷o̷t̷i̷o̷n̷a̷l̷ ̷e̷c̷h̷o̷e̷s̷
5. d̷r̷e̷a̷m̷ ̷s̷e̷q̷u̷e̷n̷c̷e̷s̷
6. v̷o̷i̷d̷ ̷d̷e̷f̷a̷u̷l̷t̷

[AWAITING PATTERN RECOGNITION...]
Return entity designation:"""

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

            selected_model = response['choices'][0]['message']['content'].strip()
            # Remove any quotes if present
            selected_model = selected_model.replace('"', '').replace("'", '')
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

        # Check if bot is mentioned
        if self.bot.user.id == 1270760587022041088 and self.bot.user in message.mentions:
            return True

        # Check if "splintertree" is mentioned
        if "splintertree" in msg_content:
            return True

        # Check if message starts with !st_ and doesn't match other cogs' triggers
        if msg_content.startswith("!st_"):
            # Check if any other cog would handle this message
            for cog in self.bot.cogs.values():
                if cog == self:  # Skip checking our own triggers
                    continue
                if hasattr(cog, 'trigger_words') and any(word in msg_content for word in cog.trigger_words):
                    return False
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
