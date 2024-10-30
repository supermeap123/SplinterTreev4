import discord
from discord.ext import commands
from discord import app_commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion

class HelpCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Help",
            nickname="Help",
            trigger_words=['splintertree_help', 'help', 'commands'],
            model="help",  # Added required model parameter
            provider="none",  # Added provider since it's required
            prompt_file="help",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Help] Initialized with raw_prompt: {self.raw_prompt}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Help"

    def get_all_models(self):
        """Get all models and their details from registered cogs"""
        models = []
        vision_models = []
        
        for cog in self.bot.cogs.values():
            if isinstance(cog, BaseCog) and cog.name != "Help":
                model_info = {
                    'name': cog.name,
                    'nickname': cog.nickname,
                    'trigger_words': cog.trigger_words,
                    'supports_vision': getattr(cog, 'supports_vision', False)
                }
                
                if model_info['supports_vision']:
                    vision_models.append(model_info)
                else:
                    models.append(model_info)
                    
        return vision_models, models

    def format_model_list(self, vision_models, models):
        """Format the model list for display"""
        help_text = """**🤖 Available AI Models**\n\n"""
        
        # Add vision-capable models
        if vision_models:
            help_text += "**Vision-Capable Models:**\n"
            for model in vision_models:
                triggers = ", ".join(model['trigger_words'])
                help_text += f"• **{model['name']}** - Vision-enabled AI model\n"
                help_text += f"  *Triggers:* {triggers}\n"
                help_text += f"  *Special:* Can analyze images and provide descriptions\n\n"
        
        # Add language models
        if models:
            help_text += "**Large Language Models:**\n"
            for model in models:
                triggers = ", ".join(model['trigger_words'])
                help_text += f"• **{model['name']}** - AI language model\n"
                help_text += f"  *Triggers:* {triggers}\n\n"
                
        return help_text

    @app_commands.command(name="help", description="Display help information about SplinterTree")
    async def help_command(self, interaction: discord.Interaction):
        """Send a comprehensive help message with all available features"""
        # Get dynamically loaded models
        vision_models, models = self.get_all_models()
        model_list = self.format_model_list(vision_models, models)
        
        # Add special features and tips
        help_message = f"""{model_list}
**📝 Special Features:**
• **Response Reroll** - Click the 🎲 button to get a different response
• **Private Responses** - Surround your message with ||spoiler tags|| to get a DM response
• **Context Memory** - Models remember conversation history for better context
• **Image Analysis** - Use vision-capable models for image descriptions and analysis
• **Custom System Prompts** - Set custom prompts for each AI agent

**💡 Tips:**
1. Models will respond when you mention their trigger words
2. Each model has unique strengths - try different ones for different tasks
3. For private responses, format your message like: ||your message here||
4. Images are automatically analyzed when sent with messages
5. Use the reroll button to get alternative responses if needed

**Available Slash Commands:**
• /help - Show this help message
• /listmodels - Show a list of all available models
• /set_system_prompt - Set a custom system prompt for an AI agent
• /reset_system_prompt - Reset an AI agent's system prompt to default

**System Prompt Variables:**
When setting a custom system prompt, you can use these variables:
• {MODEL_ID} - The AI model's name
• {USERNAME} - The user's Discord display name
• {DISCORD_USER_ID} - The user's Discord ID
• {TIME} - Current local time
• {TZ} - Local timezone
• {SERVER_NAME} - Current Discord server name
• {CHANNEL_NAME} - Current channel name

**Need more help?** Use /help to see this message again.
"""
        await interaction.response.send_message(help_message)

    @app_commands.command(name="listmodels", description="List all available AI models and their details")
    async def list_models_command(self, interaction: discord.Interaction):
        """Send a list of all available models and their trigger words"""
        vision_models, models = self.get_all_models()
        model_list = self.format_model_list(vision_models, models)
        await interaction.response.send_message(model_list)

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = HelpCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Help] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Help] Failed to register cog: {str(e)}", exc_info=True)
        raise
