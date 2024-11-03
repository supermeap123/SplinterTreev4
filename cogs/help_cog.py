import discord
from discord.ext import commands
import logging

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug("[Help] Initialized")

    def get_all_models(self):
        """Get all models and their details from registered cogs"""
        models = []
        vision_models = []

        for cog in self.bot.cogs.values():
            if hasattr(cog, 'name') and hasattr(cog, 'model') and cog.name != "Help":
                model_info = {
                    'name': cog.name,
                    'nickname': getattr(cog, 'nickname', cog.name),
                    'trigger_words': getattr(cog, 'trigger_words', []),
                    'supports_vision': getattr(cog, 'supports_vision', False),
                    'model': getattr(cog, 'model', 'Unknown'),
                    'provider': getattr(cog, 'provider', 'Unknown')
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
                help_text += f"• **{model['name']}** [{model['model']} via {model['provider']}]\n"
                help_text += f"  *Triggers:* {triggers}\n"
                help_text += f"  *Special:* Can analyze images and provide descriptions\n\n"

        # Add language models
        if models:
            help_text += "**Large Language Models:**\n"
            for model in models:
                triggers = ", ".join(model['trigger_words'])
                help_text += f"• **{model['name']}** [{model['model']} via {model['provider']}]\n"
                help_text += f"  *Triggers:* {triggers}\n\n"

        return help_text

    def format_simple_model_list(self, vision_models, models):
        """Format a simple model list with just names and models"""
        model_list = "**Available Models:**\n"

        # Add vision models with a 📷 indicator
        for model in vision_models:
            model_list += f"📷 {model['name']} - {model['model']}\n"

        # Add regular models
        for model in models:
            model_list += f"💬 {model['name']} - {model['model']}\n"

        return model_list

    @commands.command(name="splintertree_help", aliases=["help"])
    async def help_command(self, ctx):
        """Send a comprehensive help message with all available features"""
        try:
            # Get dynamically loaded models
            vision_models, models = self.get_all_models()
            model_list = self.format_model_list(vision_models, models)

            # Add special features and tips
            help_message = f"""{model_list}
**📝 Special Features:**
• **Response Reroll** - Click the 🎲 button to get a different response
• **Private Responses** - Surround your message with ||spoiler tags|| to get a DM response
• **Smart Context** - Models remember conversation history and automatically generate summaries
• **Image Analysis** - Vision-capable models provide detailed image descriptions
• **Custom System Prompts** - Set unique personalities for each AI agent
• **Agent Cloning** - Create custom variants of existing agents
• **Adaptive Memory** - Context window size adjusts per channel

**💡 Context & Memory Features:**
1. **Conversation Memory**
   • Remembers up to 10 messages by default (adjustable per channel)
   • Automatically maintains conversation flow and references
   • Includes timestamps and user information for better context

2. **Smart Summaries**
   • Automatically generates summaries every 24 hours
   • Summaries preserve important context for long-running conversations
   • Includes key decisions, topics, and interaction patterns
   • Rate-limited to prevent excessive API usage

3. **Context Management**
   • Channel-specific context windows
   • Automatic deduplication of repeated messages
   • Preserves conversation metadata (duration, message count)
   • Handles both text and image context seamlessly

**💬 Response Features:**
1. **Private Responses**
   • Use ||spoiler tags|| for private responses
   • Bot will DM you instead of responding in channel
   • Useful for sensitive or personal queries

2. **Response Quality**
   • Each model has unique capabilities and personality
   • Vision models can analyze images and provide descriptions
   • Reroll button available for alternative responses
   • Responses include emotional context (shown via reactions)

**🛠️ Available Commands:**

*General Commands:*
• `/help` or `!help` - Show this help message
• `/listmodels` or `!listmodels` - Show available models (simple list)
• `/list_agents` or `!list_agents` - Show detailed agent information
• `/uptime` or `!uptime` - Show bot uptime

*Context & Memory Commands:*
• `/set_context_window <size>` or `!setcontext <size>` - Set context window size (Admin)
• `/get_context_window` or `!getcontext` - View current context settings
• `/reset_context_window` or `!resetcontext` - Reset to default context size (Admin)
• `/summarize` or `!summarize` - Force create channel summary (Admin)
• `/getsummaries [hours]` or `!getsummaries [hours]` - View summaries, default 24h
• `/clearsummaries [hours]` or `!clearsummaries [hours]` - Clear summaries, optional hours (Admin)

*Channel Management:*
• `/activate` or `!activate` - Enable bot message processing in current channel
• `/deactivate` or `!deactivate` - Disable bot message processing in current channel
(Requires channel management or message management permissions)

*Agent Customization:*
• `/set_system_prompt <agent> <prompt>` - Set custom prompt
• `/reset_system_prompt <agent>` - Reset to default prompt
• `/clone_agent <agent> <new_name> <system_prompt>` - Create custom agent (Admin)

**🔧 System Prompt Variables:**
When setting custom prompts, you can use:
• {{MODEL_ID}} - AI model name
• {{USERNAME}} - User's display name
• {{DISCORD_USER_ID}} - User's Discord ID
• {{TIME}} - Current time
• {{TZ}} - Timezone
• {{SERVER_NAME}} - Server name
• {{CHANNEL_NAME}} - Channel name

**⚡ Performance Tips:**
1. Use vision models only when image analysis is needed
2. Prefer specific models for specialized tasks
3. Clear old context/summaries periodically
4. Use channel-specific context windows for optimal memory
5. Consider using summaries for long-running discussions
"""

            for msg in [help_message[i:i + 2000] for i in range(0, len(help_message), 2000)]:
                await ctx.send(msg)

            logging.info(f"[Help] Sent help message to user {ctx.author.name}")
        except Exception as e:
            logging.error(f"[Help] Error sending help message: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while fetching the help message. Please try again later.")

    @commands.command(name="listmodels")
    async def list_models_command(self, ctx):
        """Send a simple list of all available models"""
        try:
            vision_models, models = self.get_all_models()
            model_list = self.format_simple_model_list(vision_models, models)
            await ctx.send(model_list)
            logging.info(f"[Help] Sent model list to user {ctx.author.name}")
        except Exception as e:
            logging.error(f"[Help] Error sending model list: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while fetching the model list. Please try again later.")

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
