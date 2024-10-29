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
            trigger_words=['help', 'commands'],
            prompt_file="help",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Help] Initialized with raw_prompt: {self.raw_prompt}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Help"

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

    @commands.command(name="help", help="Displays a list of available commands and features")
    async def help_command(self, ctx):
        """Send a comprehensive help message with all available features"""
        help_message = """
**🤖 Available AI Models**

**Vision-Capable Models:**
• **Llama-3.2-11B** - Advanced vision model for image analysis
  *Triggers:* llama, llama 3, llama3
  *Special:* Can analyze images and provide descriptions

**Large Language Models:**
• **Claude-3-Opus** - Latest Claude model with enhanced capabilities
  *Triggers:* claude, claude 3, opus

• **Claude-3-Sonnet** - Balanced version of Claude 3
  *Triggers:* sonnet, claude sonnet

• **Gemini Pro** - Google's advanced language model
  *Triggers:* gemini pro, geminipro

• **Gemini** - Standard Gemini model
  *Triggers:* gemini

• **Claude-2** - Previous generation Claude
  *Triggers:* claude2, claude 2

• **Claude-1.1** - Original Claude model
  *Triggers:* claude1, claude 1

• **Grok** - xAI's conversational model
  *Triggers:* grok

• **Hermes** - Specialized language model
  *Triggers:* hermes

• **Liquid** - Fluid conversation model
  *Triggers:* liquid

• **Mythomax** - Mythological knowledge model
  *Triggers:* mythomax

• **Magnum** - Large context model
  *Triggers:* magnum

• **Ministral** - Efficient language model
  *Triggers:* ministral

• **Nemotron** - Advanced reasoning model
  *Triggers:* nemotron

• **O1-Mini** - Compact but capable model
  *Triggers:* o1mini, o1

• **OpenChat** - Open conversation model
  *Triggers:* openchat

• **R-Plus** - Enhanced reasoning model
  *Triggers:* rplus, r+

• **Sonar** - Precise language model
  *Triggers:* sonar

• **Sydney** - Conversational AI model
  *Triggers:* sydney

**📝 Special Features:**
• **Response Reroll** - Click the 🎲 button to get a different response
• **Private Responses** - Surround your message with ||spoiler tags|| to get a DM response
• **Context Memory** - Models remember conversation history for better context
• **Image Analysis** - Use Llama-3.2-11B for image descriptions and analysis

**💡 Tips:**
1. Models will respond when you mention their trigger words
2. Each model has unique strengths - try different ones for different tasks
3. For private responses, format your message like: ||your message here||
4. Images are automatically analyzed when sent with messages
5. Use the reroll button to get alternative responses if needed

**Need more help?** Just mention 'help' or use !help to see this message again.
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
