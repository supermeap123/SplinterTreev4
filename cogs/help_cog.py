import discord
from discord.ext import commands

class ContactButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(
            label="Contact Card", 
            url="https://sydney.gwyn.tel/contactcard"
        ))

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='contact')
    async def show_contact(self, ctx):
        """Show contact information with button"""
        embed = discord.Embed(
            title="Contact Information",
            description="Click the button below to view my contact card",
            color=discord.Color.blue()
        )
        view = ContactButton()
        await ctx.send(embed=embed, view=view)

    @commands.command(name='splintertree_help')
    async def splintertree_help(self, ctx):
        """Comprehensive help command showing all features, models, and commands"""
        embeds = []

        # Main Features Embed
        main_embed = discord.Embed(
            title="🌳 Splintertree Help",
            description="Complete guide to Splintertree's features and capabilities",
            color=discord.Color.green()
        )

        # Add Administrative Commands section
        admin_commands = """
        `!splintertree_help` - Show this help message
        `!toggle_shared_history` - Toggle shared message history for the channel
        `!toggle_image_processing` - Toggle image processing for the channel
        `!contact` - Show contact information
        """
        main_embed.add_field(name="👑 Administrative Commands", value=admin_commands.strip(), inline=False)

        # Add Core Features section
        features = """
        • **Shared Message History** - Agents remember conversation context
        • **Image Processing** - Automatic image description using vision models
        • **File Handling** - Support for text files and images
        • **Response Reroll** - Button to generate alternative responses
        • **Emotion Analysis** - Reactions based on message sentiment
        • **Status Updates** - Rotating status showing uptime, last interaction, and current model
        """
        main_embed.add_field(name="✨ Core Features", value=features.strip(), inline=False)

        # Add Basic Usage section
        usage = """
        • **Direct Mention** - @Splintertree for random model response
        • **Keyword Trigger** - Use "splintertree" in message for random model
        • **Model Selection** - Use specific model triggers (listed below)
        • **Image Analysis** - Simply attach an image with your message
        • **File Processing** - Attach .txt or .md files with your message
        """
        main_embed.add_field(name="📝 Basic Usage", value=usage.strip(), inline=False)
        embeds.append(main_embed)

        # Models Embed
        models_embed = discord.Embed(
            title="🤖 Available Models",
            description="List of all available AI models and their trigger words",
            color=discord.Color.blue()
        )

        # Get all available models and their capabilities
        models_info = {}
        vision_models = []
        
        for cog in self.bot.cogs.values():
            if hasattr(cog, 'name') and hasattr(cog, 'provider') and hasattr(cog, 'trigger_words'):
                provider = "OpenRouter" if cog.provider == "openrouter" else "OpenPipe"
                capabilities = []
                
                if hasattr(cog, 'supports_vision') and cog.supports_vision:
                    capabilities.append("Vision")
                    vision_models.append(cog.name)
                
                capabilities.append(provider)
                capabilities_str = " | ".join(capabilities)
                
                trigger_words = [f"`{word}`" for word in cog.trigger_words]
                trigger_str = ", ".join(trigger_words)
                
                models_info[cog.name] = f"**Capabilities:** {capabilities_str}\n**Triggers:** {trigger_str}"

        # Sort models by name and add to embed
        for name in sorted(models_info.keys()):
            models_embed.add_field(name=name, value=models_info[name], inline=False)

        embeds.append(models_embed)

        # Special Features Embed
        special_embed = discord.Embed(
            title="🎯 Special Features",
            description="Detailed information about special features and capabilities",
            color=discord.Color.gold()
        )

        # Add Vision Processing section
        vision_info = f"""
        The following models support direct image analysis:
        {', '.join(vision_models)}
        
        Other models will receive text descriptions of images processed by Llama.
        Simply attach an image to your message or reference a recent image.
        """
        special_embed.add_field(name="👁️ Vision Processing", value=vision_info.strip(), inline=False)

        # Add Context Management section
        context_info = """
        • Message history is maintained per channel
        • Default context window: 10 messages
        • Adjustable using admin commands
        • Shared across all models in channel
        • Persists between bot restarts
        """
        special_embed.add_field(name="🧠 Context Management", value=context_info.strip(), inline=False)

        # Add File Processing section
        file_info = """
        • Supports .txt and .md files
        • Automatic content extraction
        • Can be combined with image processing
        • Content included in model context
        """
        special_embed.add_field(name="📄 File Processing", value=file_info.strip(), inline=False)

        embeds.append(special_embed)

        try:
            for embed in embeds:
                await ctx.author.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I couldn't send you a DM. Please check your DM settings and try again.")

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
