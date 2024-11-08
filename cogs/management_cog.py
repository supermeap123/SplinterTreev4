import discord
from discord.ext import commands
import logging
import shlex
from datetime import datetime
from .base_cog import BaseCog

class ManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.utcnow()

    @commands.command(name="uptime")
    async def uptime(self, ctx):
        """Shows how long the bot has been running"""
        current_time = datetime.utcnow()
        delta = current_time - self.start_time
        
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        uptime_str = []
        if days > 0:
            uptime_str.append(f"{days} days")
        if hours > 0:
            uptime_str.append(f"{hours} hours")
        if minutes > 0:
            uptime_str.append(f"{minutes} minutes")
        if seconds > 0 or not uptime_str:
            uptime_str.append(f"{seconds} seconds")
            
        await ctx.send(f"🕒 Bot has been running for {', '.join(uptime_str)}")

    @commands.command(name="list_agents")
    async def list_agents(self, ctx):
        """Lists all available AI agents and their trigger words"""
        agents = []
        for cog in self.bot.cogs.values():
            if isinstance(cog, BaseCog):
                trigger_words = ", ".join(cog.trigger_words)
                agents.append(f"**{cog.name}** ({cog.nickname})\nTrigger words: {trigger_words}")

        if not agents:
            await ctx.send("No AI agents are currently available.")
            return

        # Create an embed for better formatting
        embed = discord.Embed(
            title="Available AI Agents",
            description="Here are all the available AI agents and their trigger words:",
            color=discord.Color.blue()
        )

        # Split agents into fields (Discord has a 25 field limit)
        for i in range(0, len(agents), 25):
            chunk = agents[i:i+25]
            # Join the chunk with double newlines for better spacing
            chunk_text = "\n\n".join(chunk)
            # If this isn't the first chunk, add a field
            if i == 0:
                embed.description += f"\n\n{chunk_text}"
            else:
                # Split into multiple fields if needed (each field has 1024 char limit)
                while chunk_text:
                    if len(chunk_text) <= 1024:
                        embed.add_field(name="More Agents", value=chunk_text, inline=False)
                        chunk_text = ""
                    else:
                        # Find the last complete agent entry that fits
                        split_index = chunk_text[:1024].rindex("\n\n")
                        embed.add_field(name="More Agents", value=chunk_text[:split_index], inline=False)
                        chunk_text = chunk_text[split_index+2:]

        await ctx.send(embed=embed)

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
