import discord
from discord.ext import commands
import logging
from base_cog import BaseCog

class Claude1_1Cog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot, 
                         name="Claude-1.1",
                         nickname="Claude 1.1",
                         trigger_words=["claude1.1", "claude 1.1", "claude1_1", "claude 1_1"],
                         model="anthropic/claude-instant-1.1",
                         provider="openrouter")
        logging.info(f"[{self.name}] Starting cog setup...")

    async def handle_message(self, message):
        # Let base_cog handle image processing first
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
    cog = Claude1_1Cog(bot)
    try:
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[{cog.name}] Cog is loaded and listening for triggers: {cog.trigger_words}")
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
