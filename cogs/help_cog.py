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
            if hasattr(cog, 'name') and hasattr(cog, 'model') and cog.name not in ["Help", "Context"]:
                model_info = {
                    'name': cog.name,
                    'nickname': getattr(cog, 'nickname', cog.name),
                    'trigger_words': getattr(cog, 'trigger_words', []),
                    'supports_vision': getattr(cog, 'supports_vision', False),
                    'model': getattr(cog, 'model', 'Unknown'),
                    'provider': getattr(cog, 'provider', 'Unknown'),
                    'description': getattr(cog, 'description', '')
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
                help_text += f"  *Special:* Can analyze images and provide descriptions\n"
                if model['description']:
                    help_text += f"  *Description:* {model['description']}\n\n"
                else:
                    help_text += "\n"

        # Add language models
        if models:
            help_text += "**Large Language Models:**\n"
            for model in models:
                triggers = ", ".join(model['trigger_words'])
                help_text += f"• **{model['name']}** [{model['model']} via {model['provider']}]\n"
                help_text += f"  *Triggers:* {triggers}\n"
                if model['description']:
                    help_text += f"  *Description:* {model['description']}\n\n"
                else:
                    help_text += "\n"

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

    @commands.command(name="help", aliases=["st_help"])
    async def help_command(self, ctx):
        """Send a comprehensive help message with all available features"""
        try:
            # Get dynamically loaded models
            vision_models, models = self.get_all_models()
            model_list = self.format_model_list(vision_models, models)

            # Add special features and tips
            help_message = f"""{model_list}
**📝 Special Features:**
• **Multi-Model Support** - Access a variety of AI models through OpenRouter and OpenPipe
• **Streaming Responses** - Real-time response streaming for natural conversation flow
• **Shared Context Database** - Models share conversation history for better context
• **Universal Image Processing** - Automatic image description and analysis for all models
• **File Handling** - Support for text files and images
• **Response Reroll** - Click the 🎲 button to get a different response
• **Emotion Analysis** - Reactions based on message sentiment
• **Status Updates** - Rotating status showing uptime, last interaction, and current model
• **Dynamic System Prompts** - Customizable per-channel system prompts with variable support
• **Agent Cloning** - Create custom variants of existing agents with unique system prompts
• **PST Timezone Preference** - All time-related operations use Pacific Standard Time (PST) by default
• **User ID Resolution** - Automatically resolves Discord user IDs to usernames in messages
• **Attachment-Only Processing** - Handles messages containing only attachments (images, text files)
• **Automatic Database Initialization** - Schema is automatically applied on bot startup
• **Improved Error Handling and Logging** - Enhanced error reporting for better troubleshooting
• **OpenPipe Request Reporting** - Automatic logging for analysis and model improvement
• **Message ID Tracking** - Prevents duplicate messages by tracking processed message IDs

**💡 Tips:**
1. Models will respond when you mention their trigger words
2. Each model has unique strengths - try different ones for different tasks
3. For private responses, format your message like: ||your message here||
4. Images are automatically analyzed when sent with messages
5. Use the reroll button to get alternative responses if needed
6. Manage conversation context with `!setcontext`, `!getcontext`, and `!resetcontext`
7. Clone agents to create custom AI assistants tailored to your needs
8. Use system prompt variables for dynamic and personalized prompts

**Available Commands:**
• `!help` - Show this help message
• `!listmodels` - Show all available models (simple list)
• `!list_agents` - Show all available agents with detailed info
• `!uptime` - Show how long the bot has been running
• `!set_system_prompt <agent> <prompt>` - Set a custom system prompt for an AI agent
• `!reset_system_prompt <agent>` - Reset an AI agent's system prompt to default
• `!clone_agent <agent> <new_name> <system_prompt>` - Create a new agent based on an existing one (Admin only)
• `!setcontext <size>` - Set the number of previous messages to include in context (Admin only)
• `!getcontext` - View current context window size
• `!resetcontext` - Reset context window to default size (Admin only)
• `!clearcontext [hours]` - Clear conversation history, optionally specify hours
• `!summarize` - Force create a summary for the current channel (Admin only)
• `!getsummaries [hours]` - View chat summaries for specified hours (default: 24)
• `!clearsummaries [hours]` - Clear chat summaries, optionally specify hours (Admin only)

**System Prompt Variables:**
When setting custom system prompts, you can use these variables:
• {{MODEL_ID}} - The AI model's name
• {{USERNAME}} - The user's Discord display name
• {{DISCORD_USER_ID}} - The user's Discord ID
• {{TIME}} - Current local time (PST)
• {{TZ}} - Local timezone (PST)
• {{SERVER_NAME}} - Current Discord server name
• {{CHANNEL_NAME}} - Current channel name

"""

            # Send the help message in chunks to avoid exceeding Discord's message length limit
            for msg in [help_message[i:i + 2000] for i in range(0, len(help_message), 2000)]:
                await ctx.send(msg)

            logging.info(f"[Help] Sent help message to user {ctx.author.name}")
        except Exception as e:
            logging.error(f"[Help] Error sending help message: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while fetching the help message. Please try again later.")

    @commands.command(name="listmodels", aliases=["st_listmodels"])
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

    @commands.command(name="list_agents", aliases=["st_list_agents"])
    async def list_agents_command(self, ctx):
        """Send a detailed list of all available agents and their configurations"""
        try:
            vision_models, models = self.get_all_models()
            embed = discord.Embed(title="🤖 Available Agents", color=discord.Color.blue())
            for model in vision_models + models:
                triggers = ", ".join(model['trigger_words'])
                description = f"**Model:** {model['model']} via {model['provider']}\n"
                description += f"**Triggers:** {triggers}\n"
                if model['supports_vision']:
                    description += "*Supports vision and can analyze images.*\n"
                if model['description']:
                    description += f"**Description:** {model['description']}\n"
                embed.add_field(name=model['name'], value=description, inline=False)
            await ctx.send(embed=embed)
            logging.info(f"[Help] Sent agent list to user {ctx.author.name}")
        except Exception as e:
            logging.error(f"[Help] Error sending agent list: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while fetching the agent list. Please try again later.")

async def setup(bot):
    try:
        cog = HelpCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Help] Registered cog with qualified_name: HelpCog")
        return cog
    except Exception as e:
        logging.error(f"[Help] Failed to register cog: {e}", exc_info=True)
        raise
