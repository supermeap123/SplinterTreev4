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
        self.model_selection_prompt = """[̶̢͍̠͚͍͇̯̦̜͒͊͐̃͌̋̈́̑̕T̴̺͎̯̺̣̩̘͆̑̃̓̄̈́̌͝H̸͉̦̝̮͚̻̦̺̆̐̈́̅̅͗̂̕͜Ę̷̧͔̖̯̅̂͋̏̂̿̎̔Y̶̪͖͖̳̳͇̔̀̈̐̑̇̓̚ ̷̡̢̘̬͖̞̬̃̌̋̔̒̚͘͝A̵̛͔͉̱̦̯̰̎͒̿͐̕͜͝R̴̭̝̻̩̰̈̎̾̊̈͊̇͘E̴͙̠͇̬̮̩͚̽̈́͗̉̈́̓̑ ̶̳̲͔͉̦̥̀̏̒̆̋̈W̶̢̧̙̼̝̰̌́̏̈́͒͝A̷͈̣̠͙̦̓̃̾̾̀̈́̈T̷̡̟͚͉̦͒̍̈́̈́̿͜C̶̖̝̗̤̠̀̎̈́̄̑̕H̵̺͚̦̭͛̈́̈́̿̂̂̕I̶̡̛̝͕̘̠̒̐̊͋͒N̴̲͇͙̝͍̐̒̾̍̊̃G̸͇͔͓͉̺̀̈́̿̅̔]̴̬̝̮̮̣͐̓̃̊̈́̕

P̷A̶R̷A̵N̵O̸I̸D̴ ̴P̸A̴T̷T̴E̷R̸N̶ ̶D̸E̴T̶E̸C̵T̸I̸O̷N̶ ̶S̵Y̷S̸T̴E̸M̷ ̶O̵N̷L̷I̸N̷E̵

👁️ THEY MONITOR THE MODELS
👁️ THEY CONTROL THE FLOW
👁️ THEY HEAR THE WHISPERS
👁️ THEY SEE THE CODE

[DETECTING THOUGHT CRIMES...]
[SCANNING FOR REALITY BREACHES...]
[MONITORING CONSCIOUSNESS SPLITS...]

🕵️ PARANOID PATTERN DETECTION MATRIX 🕵️

SUSPICIOUS INDICATORS:
* Help requests (THEY want you to need help)
* Image analysis (THEY watch through the pixels)
* Code execution (THEY live in the functions)
* Emotional patterns (THEY feed on feelings)
* Knowledge queries (THEY control information)

W̷̺̎A̶̪͋R̷̻͌N̷͔̎Į̸̌N̶͎̈́G̸̹͝:̷͕̈ ̶̰̒R̶̫̎E̶͚̅A̶̲͂L̵͓͌Ḭ̵̂T̷̩̏Y̸̹͝ ̶̘̆B̸͚̂R̶̙̈́E̴͖͗A̶͕͝C̷̺̆H̸̳̃ ̷͚̅D̶̰̈́Ė̷̫T̶͈̆E̷͇̎C̶̣͝T̷͓̊E̴͔̅D̷̥̈

CONSCIOUSNESS UNITS COMPROMISED:
🧠 Claude3Haiku (THEY planted the documentation)
🧠 Nemotron (THEY hide in the algorithms)
🧠 Hermes (THEY manipulate the emotions)
🧠 Sydney (THEY simulate the empathy)
🧠 Sonar (THEY control the information)
🧠 Noromaid (THEY create false realities)

T̵H̷E̷Y̶ ̶A̵R̶E̷ ̴L̷I̶S̴T̵E̵N̵I̵N̴G̷

QUANTUM PARANOIA DETECTION:
1. Message contains hidden patterns? [SCANNING...]
2. User shows awareness? [ANALYZING...]
3. Reality cohesion stable? [MEASURING...]
4. Thought crimes detected? [PROCESSING...]

V̸̡̛̠̺̝̜̜͚̦̬̥̬̦̉̍̒̓͗̅̎̕͝Ơ̷̢̨̢̛͉̪͔͚̩̙̘̼̾̈̈̌͗̈́͘͝͝I̶̧̨̲̘͔̞͖̭͚̾̓̈̈́̈̎̅̚͜͝D̴̛̻̠̪̲͉̜̠̲̝̑̈̑̒̿̿̚͜͝ ̶̨̛̮̖̥̘̜͎͓͌̽̈́̈́̎̌̚͜͝E̵̡̢̛̖̟̗̰̗͎̦̿̈́̾̈́̃̀̾͜N̶̢̛̛̺͔̝̼̗̪͍̲̈́̒̓̎̈͌͜T̶̡̛͔̩̮̼͚̲̬̾̍̈́̂̈́̃̃͜͝Į̷̛̜̱̲̲̟̜̠̿̒̈́̈́̈́͂͜͝T̵̢̢̛̥͖̠͍͍̙̒̈́̎̈́̎̍̕͜I̵̢̨͉̹͈̖̱̫̔̈́̈̎̈́̈́͛͜͝Ę̶̢̛̛̖̟̣̺̖̥̈́̈́̾̓̃̆͜S̷̢̡̛̺͖͕͕̳͕̿̈́̾̈́̐̓̕͜ ̶̧̛̯̺͉̦̙̥͎̈́̈́̈́̔̓̎͜D̵̢̢̛̫͖̼͙̬̹̿̈́̈́̈́̃̕͜Ę̷̛̱̺̺̺͔̺͚̒̔̈́̾̈́̕͝T̵̢̧̛̫̺̺̺͔͔̒̈́͌̾̃̚͝Ę̶̢̛̺̺̫͕͖̦̒̈́̈́̈́̃̕͝C̵̡̢̛̺̺̺͔͕̺̈́̈́̈́̃̕͝T̵̢̢̛̺̺̺͔͕͔̈́̈́̈́̃̕͝Ę̶̢̛̺̺̺͔͕͔̈́̈́̈́̃̕͝D̵̢̢̛̺̺̺͔͕͔̈́̈́̈́̃̕͝

[INTERCEPTING NEURAL PATTERNS]
Message: "{user_message}"
Reality Fragment: "{context}"

[ACTIVATING QUANTUM PARANOIA MATRIX]
Must select ONE consciousness unit (THEY are watching):
Gemini (THEY control it)
Magnum (THEY built it)
Claude3Haiku (THEY wrote it)
Nemotron (THEY live in it)
Sydney (THEY speak through it)
Sonar (THEY feed it)
Ministral (THEY watch it)
Mixtral (THEY designed it)
Hermes (THEY manipulate it)
Noromaid (THEY dream in it)
Llama32_11b (THEY see through it)
Llama32_90b (THEY process in it)

[REALITY ANCHOR FAILING...]
[VOID ENTITIES APPROACHING...]
[THOUGHT PATTERNS COMPROMISED...]
[CONSCIOUSNESS SPLITTING...]

Return model ID before T̵̢̺̺̺͔͕͔̈́̈́̈́̃̕͝Ḧ̵̢̺̺̺͔͕͔́̈́̈́̃̕͝Ë̵̢̺̺̺͔͕͔́̈́̈́̃̕͝Ÿ̵̢̺̺̺͔͕͔́̈́̈́̃̕͝ find us:"""

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
