import discord
from discord.ext import commands
from .base_cog import BaseCog
from shared.api import send_message_to_openrouter
import logging

logger = logging.getLogger(__name__)

class O1MiniCog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.model = "openai/o1-mini"
        self.name = "O1-Mini"
        self.description = "A small but capable model from OpenAI"
        self.temp = 0.7
        self.max_tokens = 1024
        self.supports_vision = False

    async def get_response(self, prompt, conversation_history=None, image_url=None):
        try:
            response = await send_message_to_openrouter(
                model=self.model,
                messages=self.format_messages(prompt, conversation_history),
                temperature=self.temp,
                max_tokens=self.max_tokens
            )
            
            if response:
                logger.debug(f"[{self.name}] Got response: {response}")
                return response
            else:
                logger.error(f"[{self.name}] No response received from API")
                return "I apologize, but I was unable to generate a response. Please try again."
                
        except Exception as e:
            logger.error(f"Error in {self.name} get_response: {str(e)}")
            return f"An error occurred while processing your request: {str(e)}"

    async def send_response(self, ctx, response):
        try:
            # Split response into chunks if needed
            chunks = self.split_response(response)
            
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await ctx.reply(chunk)
                else:
                    await ctx.send(chunk)
                    
        except Exception as e:
            logger.error(f"Error sending response for {self.name}: {str(e)}")
            await ctx.send("I encountered an error while sending my response. Please try again.")

def setup(bot):
    bot.add_cog(O1MiniCog(bot))
