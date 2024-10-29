import discord
from discord.ext import commands
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

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return

        # Add message to context before processing
        if self.context_cog:
            try:
                channel_id = str(message.channel.id)
                guild_id = str(message.guild.id) if message.guild else None
                user_id = str(message.author.id)
                content = message.content
                is_assistant = False
                persona_name = self.name
                emotion = None

                await self.context_cog.add_message_to_context(
                    channel_id=channel_id,
                    guild_id=guild_id,
                    user_id=user_id,
                    content=content,
                    is_assistant=is_assistant,
                    persona_name=persona_name,
                    emotion=emotion
                )
            except Exception as e:
                logging.error(f"[Help] Failed to add message to context: {str(e)}")

        # Let base_cog handle message processing
        await super().handle_message(message)

    @commands.command(name="listmodels", help="Lists all available AI models and their trigger words")
    async def list_models_command(self, ctx):
        """Send a list of all available models and their trigger words"""
        vision_models, models = self.get_all_models()
        model_list = self.format_model_list(vision_models, models)
        await ctx.send(model_list)

    @commands.command(name="splintertree_help", help="Displays a list of available commands and features")
    async def help_command(self, ctx):
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

**💡 Tips:**
1. Models will respond when you mention their trigger words
2. Each model has unique strengths - try different ones for different tasks
3. For private responses, format your message like: ||your message here||
4. Images are automatically analyzed when sent with messages
5. Use the reroll button to get alternative responses if needed

**Available Commands:**
• !splintertree_help - Show this help message
• !listmodels - Show a list of all available models and their trigger words

**Need more help?** Just mention 'splintertree_help' or use !splintertree_help to see this message again.
"""
        await ctx.send(help_message)

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
