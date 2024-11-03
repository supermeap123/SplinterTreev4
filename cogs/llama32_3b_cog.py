import discord
from discord.ext import commands
import logging
from base_cog import BaseCog

class Llama32_3B_Cog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Llama-3.2-3B",
            nickname="Llama 3.2 3B",
            trigger_words=[],
            model="meta-llama/llama-3.2-3b-instruct:free",
            provider="openrouter"
        )
        logging.info(f"[{self.name}] Starting cog setup...")

    async def handle_message(self, message):
        # This cog doesn't respond directly to messages, only summarizes
        pass

    async def summarize_messages(self, messages, max_tokens=300):
        """Summarize a list of messages using the Llama 3.2 3B model."""
        try:
            if not messages:
                return "No messages to summarize."

            # Format messages for the API
            formatted_messages = []
            for message in messages:
                role = "assistant" if message['is_assistant'] else "user"
                formatted_messages.append({"role": role, "content": message['content']})

            # Call the API
            response_stream = await self.api_client.call_openrouter(
                messages=formatted_messages,
                model=self.model,
                temperature=0.1,  # Low temperature for summarization
                max_tokens=max_tokens,
                stream=True
            )
            
            full_response = ""
            async for chunk in response_stream:
                full_response += chunk
            return full_response
        except Exception as e:
            logging.error(f"[{self.name}] Error summarizing messages: {e}")
            return f"Error summarizing: {e}"


async def setup(bot):
    cog = Llama32_3B_Cog(bot)
    try:
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
