import discord
from discord.ext import commands
from .base_cog import BaseCog

class LiquidCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Liquid",
            nickname="Liquid",
            trigger_words=['liquid', 'liquid moe', '40b'],
            model="liquid/lfm-40b:free",
            provider="openrouter",
            prompt_file="liquid",
            supports_vision=False
        )

    async def process_message(self, message):
        """Override process_message to handle conversation history differently"""
        messages = [{"role": "system", "content": self.formatted_prompt(message)}]
        msg_content = f"@{message.author.display_name} {message.content}"

        # Add text message
        messages.append({"role": "user", "content": msg_content})
        
        # Add to history but don't include in API call
        self.add_to_history(message.channel.id, {
            "role": "user",
            "content": msg_content,
            "name": message.author.display_name
        })

        return messages

async def setup(bot):
    await bot.add_cog(LiquidCog(bot))
