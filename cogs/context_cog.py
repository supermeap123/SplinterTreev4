import discord
from discord.ext import commands
from config import CONTEXT_WINDOWS, DEFAULT_CONTEXT_WINDOW, MAX_CONTEXT_WINDOW
import json

class ContextCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='setcontext')
    @commands.has_permissions(manage_messages=True)
    async def set_context_window(self, ctx, size: int):
        """Set the context window size for the current channel"""
        if size < 1 or size > MAX_CONTEXT_WINDOW:
            await ctx.reply(f"❌ Context window size must be between 1 and {MAX_CONTEXT_WINDOW}")
            return

        channel_id = str(ctx.channel.id)
        CONTEXT_WINDOWS[channel_id] = size
        
        # Save to file to persist across restarts
        try:
            with open('context_windows.json', 'w') as f:
                json.dump(CONTEXT_WINDOWS, f)
        except Exception as e:
            await ctx.reply("⚠️ Warning: Could not persist context window settings")
        
        await ctx.reply(f"✅ Context window size for this channel set to {size} messages")

    @commands.command(name='getcontext')
    async def get_context_window(self, ctx):
        """Get the current context window size for this channel"""
        channel_id = str(ctx.channel.id)
        size = CONTEXT_WINDOWS.get(channel_id, DEFAULT_CONTEXT_WINDOW)
        await ctx.reply(f"📝 Current context window size: {size} messages")

    @commands.command(name='resetcontext')
    @commands.has_permissions(manage_messages=True)
    async def reset_context_window(self, ctx):
        """Reset the context window size to default for this channel"""
        channel_id = str(ctx.channel.id)
        if channel_id in CONTEXT_WINDOWS:
            del CONTEXT_WINDOWS[channel_id]
            
            # Save to file to persist across restarts
            try:
                with open('context_windows.json', 'w') as f:
                    json.dump(CONTEXT_WINDOWS, f)
            except Exception as e:
                await ctx.reply("⚠️ Warning: Could not persist context window settings")
            
        await ctx.reply(f"✅ Context window size reset to default ({DEFAULT_CONTEXT_WINDOW} messages)")

async def setup(bot):
    await bot.add_cog(ContextCog(bot))
