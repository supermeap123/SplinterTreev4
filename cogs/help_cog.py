import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import config

class Help_cog(BaseCog, name="HelpCog"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        try:
            embed = discord.Embed(title="SplinterTree Help", description="Here's how to use SplinterTree:", color=discord.Color.blue())
            embed.add_field(name="Available Models", value="Use `!models` to see a list of available models.", inline=False)
            embed.add_field(name="Using a Model", value="To use a model, type its name in brackets followed by your prompt. For example: `[Gemini] Write a short story about a robot learning to love.`", inline=False)
            embed.add_field(name="Setting Temperature", value="You can set the temperature for a model using the `!temp` command. For example: `!temp Gemini 0.5`.  See available temperatures with !temps", inline=False)
            embed.add_field(name="Context", value="To view your current context, use the command `!context`. To clear your context, use the command `!clear`. To set your context window size, use the command `!window`. To view available context window sizes, use the command `!windows`", inline=False)
            embed.add_field(name="Image Support", value="Some models support images.  Append your image to your query. For example: `[GeminiPro] Describe this image.`", inline=False)
            embed.add_field(name="Getting Help", value="If you need further assistance, please contact Gwyneth or refer to the project's README.", inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            logging.error(f"[Help] Error sending help message: {str(e)}")
            await ctx.send("An error occurred while fetching the help message. Please try again later.")


    @commands.command(name="models")
    async def model_list_command(self, ctx: commands.Context):
        try:
            model_list = ""
            for cog_name, cog in self.bot.cogs.items():
                if hasattr(cog, 'model'):
                    model_list += f"- **{cog.name}**: `{cog.model}` (Vision: {getattr(cog, 'supports_vision', False)})\n"
            if model_list:
                embed = discord.Embed(title="Available Models", description=model_list, color=discord.Color.green())
                await ctx.send(embed=embed)
            else:
                await ctx.send("No models are currently available.")
        except Exception as e:
            logging.error(f"[Help] Error sending model list: {str(e)}")
            await ctx.send("An error occurred while fetching the model list. Please try again later.")

async def setup(bot):
    try:
        await bot.add_cog(Help_cog(bot))
        logging.info("Loaded help cog")
    except Exception as e:
        logging.error(f"Failed to load help cog: {str(e)}")
