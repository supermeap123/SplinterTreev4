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

    @commands.command(name="st_help", aliases=["help"])
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
    • **Context Memory** - Models remember conversation history for better context
    • **Duplicate Message Prevention** - A message ID tracking system prevents the bot from sending duplicate messages.
    • **Image Analysis** - Use vision-capable models for image descriptions and analysis
    • **Custom System Prompts** - Set custom prompts for each AI agent
    • **Agent Cloning** - Create custom variants of existing agents with unique system prompts
    • **Chat Summaries** - Automatically summarizes chat history for better context

    **💡 Tips:**
    1. Models will respond when you mention their trigger words
    2. Each model has unique strengths - try different ones for different tasks
    3. For private responses, format your message like: ||your message here||
    4. Images are automatically analyzed when sent with messages
    5. Use the reroll button to get alternative responses if needed
    6. Chat summaries help maintain context over longer conversations

    **Available Commands:**
    • `!st_help` - Show this help message
    • `!st_listmodels` - Show all available models (simple list)
    • `!st_list_agents` - Show all available agents with detailed info (formatted embed)
    • `!st_uptime` - Show how long the bot has been running
    • `!st_set_system_prompt agent prompt` - Set a custom system prompt for an AI agent
    • `!st_reset_system_prompt agent` - Reset an AI agent's system prompt to default
    • `!st_clone_agent agent new_name system_prompt` - Create a new agent based on an existing one (Admin only)
    • `!st_setcontext size` - Set the number of previous messages to include in context (Admin only)
    • `!st_getcontext` - View current context window size
    • `!st_resetcontext` - Reset context window to default size (Admin only)
    • `!st_clearcontext [hours]` - Clear conversation history, optionally specify hours (Admin only)
    • `!st_summarize` - Force create a summary for the current channel (Admin only)
    • `!st_getsummaries [hours]` - View chat summaries for specified hours (default: 24)
    • `!st_clearsummaries [hours]` - Clear chat summaries, optionally specify hours (Admin only)


    **System Prompt Variables:**
    When setting custom system prompts, you can use these variables:
    • {{MODEL_ID}} - The AI model's name
    • {{USERNAME}} - The user's Discord display name
    • {{DISCORD_USER_ID}} - The user's Discord ID
    • {{TIME}} - Current local time
    • {{TZ}} - Local timezone
    • {{SERVER_NAME}} - Current Discord server name
    • {{CHANNEL_NAME}} - Current channel name


    **OpenRouter Models:**
    • **Magnum**: A series of models designed to replicate the prose quality of the Claude 3 models, specifically Sonnet(https://openrouter.ai/anthropic/claude-3.5-sonnet) and Opus(https://openrouter.ai/anthropic/claude-3-opus). The model is fine-tuned on top of Qwen2.5 72B. Trigger word: "magnum". Note: Sometimes Magnum thinks it's from Anthropic but it's really from anthracite-org.
    • **Gemini Pro**: Google's advanced model. Trigger word: "gemini"
    • **Mistral**: Ministral 8B is an 8B parameter model featuring a unique interleaved sliding-window attention pattern for faster, memory-efficient inference. Designed for edge use cases, it supports up to 128k context length and excels in knowledge and reasoning tasks. It outperforms peers in the sub-10B category, making it perfect for low-latency, privacy-first applications. Trigger word: "mistral"
    • **Llama-2**: The Llama 90B Vision model is a top-tier, 90-billion-parameter multimodal model designed for the most challenging visual reasoning and language tasks. It offers unparalleled accuracy in image captioning, visual question answering, and advanced image-text comprehension. Pre-trained on vast multimodal datasets and fine-tuned with human feedback, the Llama 90B Vision is engineered to handle the most demanding image-based AI tasks. This model is perfect for industries requiring cutting-edge multimodal AI capabilities, particularly those dealing with complex, real-time visual and textual analysis. Usage of this model is subject to Meta's Acceptable Use Policy. Trigger word: "llama2"
    • **NoroMaid-20B**: A collab between IkariDev and Undi. This merge is suitable for RP, ERP, and general knowledge. Trigger word: "noromaid"
    • **MythoMax-L2-13B**: One of the highest performing and most popular fine-tunes of Llama 2 13B, with rich descriptions and roleplay. Trigger word: "mythomax"
    • **Grok**: Terrible bot from xai. It thinks it's from Hitchhikers Guide to the Galaxy. Trigger word: "grok"

    **OpenPipe Models:**
    • **Hermes**: Hermes 3 is a generalist language model with many improvements over Hermes 2, including advanced agentic capabilities, much better roleplaying, reasoning, multi-turn conversation, long context coherence, and improvements across the board. Hermes 3 405B is a frontier-level, full-parameter finetune of the Llama-3.1 405B foundation model, focused on aligning LLMs to the user, with powerful steering capabilities and control given to the end user. The Hermes 3 series builds and expands on the Hermes 2 set of capabilities, including more powerful and reliable function calling and structured output capabilities, generalist assistant capabilities, and improved code generation skills. Hermes 3 is competitive, if not superior, to Llama-3.1 Instruct models at general capabilities, with varying strengths and weaknesses attributable between the two. Trigger word: "hermes"
    • **Sonar**: Llama 3.1 Sonar is Perplexity's latest model family. It surpasses their earlier Sonar models in cost-efficiency, speed, and performance. The model is built upon the Llama 3.1 405B and has internet access. Trigger word: "sonar"
    • **Liquid**: Liquid's 40.3B Mixture of Experts (MoE) model. Liquid Foundation Models (LFMs) are large neural networks built with computational units rooted in dynamic systems. LFMs are general-purpose AI models that can be used to model any kind of sequential data, including video, audio, text, time series, and signals. Trigger word: "liquid"
    • **O1-Mini**: The latest and strongest model family from OpenAI, o1 is designed to spend more time thinking before responding. The o1 models are optimized for math, science, programming, and other STEM-related tasks. They consistently exhibit PhD-level accuracy on benchmarks in physics, chemistry, and biology. Note: This model is currently experimental and not suitable for production use-cases, and may be heavily rate-limited. Trigger word: "o1mini"
    • **MOA**: The latest and strongest model family from OpenPipe, moa is designed to spend more time thinking before responding. Trigger word: "moa"
    """

            for msg in [help_message[i:i + 2000] for i in range(0, len(help_message), 2000)]:
                await ctx.send(msg)

            logging.info(f"[Help] Sent help message to user {ctx.author.name}")
        except Exception as e:
            logging.error(f"[Help] Error sending help message: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while fetching the help message. Please try again later.")

    @commands.command(name="st_listmodels")
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
