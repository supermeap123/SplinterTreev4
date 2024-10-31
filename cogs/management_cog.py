import discord
from discord.ext import commands
import logging
import shlex

class ManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clone_agent")
    @commands.has_permissions(administrator=True)
    async def clone_agent(self, ctx, *, args=None):
        """Clone an existing agent with a new name and system prompt
        Usage: !clone_agent <agent_name> <new_name> <system_prompt>"""
        try:
            if not args:
                await ctx.send("❌ Please provide the agent name, new name, and system prompt.")
                return

            # Parse arguments using shlex to handle quoted strings
            try:
                parsed_args = shlex.split(args)
            except ValueError as e:
                await ctx.send(f"❌ Error parsing arguments: {str(e)}")
                return

            if len(parsed_args) < 3:
                await ctx.send("❌ Please provide all required arguments: agent_name, new_name, and system_prompt.")
                return

            agent_name = parsed_args[0]
            new_name = parsed_args[1]
            system_prompt = " ".join(parsed_args[2:])

            # Find the original agent cog
            original_cog = None
            for cog in self.bot.cogs.values():
                if hasattr(cog, 'name') and cog.name.lower() == agent_name.lower():
                    original_cog = cog
                    break

            if not original_cog:
                await ctx.send(f"❌ Agent '{agent_name}' not found.")
                return

            # Create new trigger words based on new name
            new_trigger_words = [new_name.lower()]

            # Create new cog instance with same model but new name and prompt
            new_cog = type(original_cog)(
                bot=self.bot,
                name=new_name,
                nickname=new_name,
                trigger_words=new_trigger_words,
                model=original_cog.model,
                provider=original_cog.provider,
                supports_vision=original_cog.supports_vision
            )

            # Set the custom system prompt
            new_cog.raw_prompt = system_prompt

            # Add the new cog to the bot
            await self.bot.add_cog(new_cog)
            await ctx.send(f"✅ Successfully cloned {agent_name} as {new_name} with custom system prompt.")

        except Exception as e:
            logging.error(f"Error cloning agent: {str(e)}")
            await ctx.send(f"❌ Failed to clone agent: {str(e)}")

async def setup(bot):
    await bot.add_cog(ManagementCog(bot))
