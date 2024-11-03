import discord
from discord.ext import commands
import logging
from base_cog import BaseCog

class Claude2Cog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot,
                         name="Claude-2",
                         nickname="Claude 2",
                         trigger_words=['claude2', 'claude 2', 'splintertree', 'SplinterTree#8648', '1270760587022041088'],
                         model="anthropic/claude-2",
                         provider="openrouter")
        logging.info(f"[{self.name}] Starting cog setup...")

    async def handle_message(self, message):
        is_mentioned = self.bot.user in message.mentions
        has_keyword = any(trigger.lower() in message.content.lower() for trigger in self.trigger_words)

        if is_mentioned or has_keyword:
            await super().handle_message(message)

        # Let base_cog handle message processing
        # await super().handle_message(message) # Already handled above if mentioned or keyword present


async def setup(bot):
    cog = Claude2Cog(bot)
    try:
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[{cog.name}] Cog is loaded and listening for triggers: {cog.trigger_words}")
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
