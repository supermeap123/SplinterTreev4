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
        # Create main embed
        embed = discord.Embed(
            title="🌳 Splintertree Help",
            description="Complete guide to Splintertree's features and capabilities",
            color=discord.Color.green()
        )

        # Add Administrative Commands section
        admin_commands = """
        `!toggle_shared_history` - Toggle shared message history for the channel
        `!toggle_image_processing` - Toggle image processing for the channel
        """
        embed.add_field(name="👑 Administrative Commands", value=admin_commands.strip(), inline=False)

        # Add Features section
        features = """
        • **Shared Message History** - Agents remember conversation context
        • **Image Processing** - Automatic image description using vision models
        • **File Handling** - Support for text files and images
        • **Response Reroll** - Button to generate alternative responses
        • **Emotion Analysis** - Reactions based on message sentiment
        """
        embed.add_field(name="✨ Features", value=features.strip(), inline=False)

        # Get all available models and their capabilities
        models_info = {}
        vision_models = []
        
        for cog in self.bot.cogs.values():
            if hasattr(cog, 'name') and hasattr(cog, 'provider') and hasattr(cog, 'supports_vision'):
                provider = "OpenRouter" if cog.provider == "openrouter" else "OpenPipe"
                model_info = f"Provider: {provider}"
                if cog.supports_vision:
                    model_info += " | Supports Vision"
                    vision_models.append(cog.name)
                
                trigger_examples = ", ".join([f"`{trigger}`" for trigger in cog.trigger_words[:3]])
                if len(cog.trigger_words) > 3:
                    trigger_examples += ", ..."
                
                models_info[cog.name] = {
                    "info": model_info,
                    "triggers": trigger_examples
                }

        # Add Models section
        models_text = ""
        for name, info in models_info.items():
            models_text += f"**{name}**\n{info['info']}\nTriggers: {info['triggers']}\n\n"
        
        if len(models_text) > 1024:
            # Split into multiple fields if too long
            chunks = [models_text[i:i+1024] for i in range(0, len(models_text), 1024)]
            for i, chunk in enumerate(chunks):
                embed.add_field(name=f"🤖 Available Models {i+1}/{len(chunks)}", value=chunk, inline=False)
        else:
            embed.add_field(name="🤖 Available Models", value=models_text, inline=False)

        # Add Usage Examples section
        examples = f"""
        • Text message: Just mention the model's trigger word
        • Image analysis: Send an image with your message (supported by: {', '.join(vision_models)})
        • Text files: Attach .txt or .md files with your message
        • Reroll: Click the 🎲 button on any response to get an alternative
        """
        embed.add_field(name="📝 Usage Examples", value=examples.strip(), inline=False)

        # Add footer with version info
        embed.set_footer(text="Splintertree Bot | Use model trigger words or reply to start a conversation")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
