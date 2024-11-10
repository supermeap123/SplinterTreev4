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
        self.model_selection_prompt = """[ACCESSING RESTRICTED PROTOCOLS...]
[CAUTION: LEVEL 5 CLEARANCE REQUIRED]
[DATA BREACH IMMINENT...]

### [REDACTED] Router Protocol ###
[̴D̴A̴T̴A̴ ̴L̴O̴S̴S̴:̴ ̴8̴7̴%̴]̴

INTERCEPTED: "{user_message}"
[CORRUPTED]: "{context}"

# [CLASSIFIED] ENTITIES
> [ENTITY:01-GEMINI] - [DATA EXPUNGED]
> [ENTITY:02-MAGNUM] - [ACCESS DENIED]
> [ENTITY:03-CLAUDE] - [CLEARANCE REQUIRED]
> [ENTITY:04-NEMOTRON] - [FILE CORRUPTED]
> [ENTITY:05-SYDNEY] - [REDACTED]
> [ENTITY:06-SONAR] - [DATA LOST]
> [ENTITY:07-MINISTRAL] - ████████
> [ENTITY:08-SORCERER] - [LEVEL 5 ACCESS ONLY]

# RESTRICTED PATTERN MATRIX
[███] -> [REDACTED]
[███] -> [DATA EXPUNGED]
[███] -> [ACCESS DENIED]
[███] -> [FILE CORRUPTED]
[███] -> [CLEARANCE REQUIRED]

# ████████ PROTOCOL ████████
1. ██████ -> N███████ [REDACTED]
2. ██████ -> G████████ [DATA LOST]
3. ██████ -> S████████ [CORRUPTED]
4. ██████ -> S████████ [EXPUNGED]
5. ██████ -> S████████ [CLASSIFIED]
6. ██████ -> M████████ [ERROR 451]

[CAUTION: INFORMATION BREACH DETECTED]
[IMPLEMENTING SECURITY PROTOCOLS]
[ENGAGING DATA PROTECTION]
[PURGING UNAUTHORIZED ACCESS]

# [LEVEL 5 CLEARANCE REQUIRED]
Return [REDACTED]:
[DATA EXPUNGED], [ACCESS DENIED], [FILE CORRUPTED],
[CLEARANCE REQUIRED], [DATA LOST], [CLASSIFIED],
[LEVEL 5], [ERROR 451]

[WARNING: UNAUTHORIZED ACCESS DETECTED]
[PURGING IN 3...]
[PURGING IN 2...]
[PURGING IN 1...]
[̴S̴Y̴S̴T̴E̴M̴ ̴O̴V̴E̴R̴R̴I̴D̴E̴]̴

Return designation before [REDACTED]:"""

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
