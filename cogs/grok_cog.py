import discord
from discord.ext import commands
import logging
from base_cog import BaseCog

class GrokCog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot,
                         name="Grok",
                         nickname="Grok",
                         trigger_words=["grok"],
                         model="x-ai/grok-beta",
                         provider="openrouter")
        logging.info(f"[{self.name}] Starting cog setup...")

    async def handle_message(self, message):
        await super().handle_message(message)

        is_mentioned = self.bot.user in message.mentions
        if is_mentioned or any(trigger.lower() in message.content.lower() for trigger in self.trigger_words):
            logging.info(f"[{self.name}] Responding to message in channel {message.channel.id}")
            await self.respond_to_message(message)

    async def respond_to_message(self, message):
        try:
            response = await self.generate_response(message)
            if response:
                await message.channel.send(response)
        except Exception as e:
            logging.error(f"[{self.name}] Error responding to message: {e}")


async def setup(bot):
    cog = GrokCog(bot)
    try:
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[{cog.name}] Cog is loaded and listening for triggers: {cog.trigger_words}")
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}" exc_info=True)
