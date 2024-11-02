import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Shows help information about bot commands and features"
    )
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Bot Help",
            description="Here are the available commands and features:",
            color=discord.Color.blue()
        )

        # Basic Usage
        embed.add_field(
            name="Basic Usage",
            value="Simply mention the bot (@Bot) followed by your message to start a conversation.",
            inline=False
        )

        # Model Selection
        embed.add_field(
            name="/model [model_name]",
            value="Change the AI model. Available models:\n" +
                  "- sydney (default)\n" +
                  "- claude2\n" +
                  "- claude3opus\n" +
                  "- claude3sonnet\n" +
                  "- gemini\n" +
                  "- geminipro\n" +
                  "- gemma\n" +
                  "- grok\n" +
                  "- hermes\n" +
                  "- liquid\n" +
                  "- llama32_3b\n" +
                  "- llama32_11b\n" +
                  "- magnum\n" +
                  "- ministral\n" +
                  "- moa\n" +
                  "- mythomax\n" +
                  "- nemotron\n" +
                  "- noromaid\n" +
                  "- o1mini\n" +
                  "- openchat\n" +
                  "- rplus\n" +
                  "- sonar",
            inline=False
        )

        # Temperature Setting
        embed.add_field(
            name="/temperature [0.0-2.0]",
            value="Adjust the creativity level of responses (0.0 = more focused, 2.0 = more creative). Default is 0.7",
            inline=False
        )

        # Channel Management
        embed.add_field(
            name="Channel Management",
            value="**/activate** - Enable bot message processing in the current channel\n" +
                  "**/deactivate** - Disable bot message processing in the current channel\n" +
                  "(Requires channel management or message management permissions)",
            inline=False
        )

        # Context Management
        embed.add_field(
            name="Context Management",
            value="**/context clear** - Clear conversation history\n" +
                  "**/context show** - Show current conversation history",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
