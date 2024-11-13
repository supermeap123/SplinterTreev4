import logging
import discord
from discord.ext import commands
from shared.api import api
from shared.utils import get_prompt_from_file, get_temperature_for_model

class Llama8bCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model = "workers/@cf/meta/llama-3.1-8b-instruct"
        self.name = "llama8b"
        self.description = "Llama 3.1 8B Instruct - A smaller but capable Llama model"
        self.temperature = 0.7
        self.max_tokens = 1024
        self.supports_images = False
        self.supports_functions = False
        self.supports_vision = False

    @commands.command(name='llama8b', aliases=['l8b'])
    async def llama8b(self, ctx, *, prompt):
        """Llama 3.1 8B Instruct - A smaller but capable Llama model"""
        logging.info(f"[Llama8b] Received prompt from {ctx.author}: {prompt}")
        
        # Get custom temperature if set
        temperature = get_temperature_for_model(self.name) or self.temperature
        
        # Get custom prompt if available
        system_prompt = get_prompt_from_file(self.name)
        
        try:
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Send typing indicator
            async with ctx.typing():
                # Stream the response
                response_text = ""
                message = None
                
                async for chunk in api.call_openpipe(
                    messages=messages,
                    model=self.model,
                    temperature=temperature,
                    max_tokens=self.max_tokens,
                    stream=True,
                    user_id=str(ctx.author.id),
                    guild_id=str(ctx.guild.id) if ctx.guild else None,
                    prompt_file=system_prompt,
                    model_cog=self.name
                ):
                    response_text += chunk
                    
                    # Update message every 10 tokens (roughly)
                    if len(response_text.split()) % 10 == 0:
                        if message:
                            try:
                                await message.edit(content=response_text)
                            except discord.errors.HTTPException:
                                # If message is too long, send a new one
                                message = await ctx.send(response_text)
                        else:
                            message = await ctx.send(response_text)
                
                # Final update
                if message:
                    try:
                        await message.edit(content=response_text)
                    except discord.errors.HTTPException:
                        await ctx.send(response_text)
                else:
                    await ctx.send(response_text)
                
                logging.info(f"[Llama8b] Sent response to {ctx.author}")
        
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logging.error(f"[Llama8b] {error_msg}")
            if not message:
                await ctx.send(error_msg)
            else:
                await message.edit(content=error_msg)

async def setup(bot):
    await bot.add_cog(Llama8bCog(bot))
    logging.info("[Llama8b] Cog loaded")
