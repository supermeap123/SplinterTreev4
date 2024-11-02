import discord
from discord.ext import commands
from discord import app_commands
from config import CONTEXT_WINDOWS, DEFAULT_CONTEXT_WINDOW, MAX_CONTEXT_WINDOW
import sqlite3
import json
import logging
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional
import textwrap
import backoff

class ContextCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'databases/interaction_logs.db'
        self._setup_database()
        self.summary_chunk_hours = 24  # Summarize every 24 hours of chat
        self.last_summary_check = {}  # Track last summary generation per channel
        self.summary_locks = {}  # Lock per channel for summary generation
        self.llama_cog = None  # Will be set when Llama cog is loaded

    def _setup_database(self):
        """Ensure database and tables exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load and execute schema if needed
                with open('databases/schema.sql', 'r') as f:
                    conn.executescript(f.read())
        except Exception as e:
            logging.error(f"Failed to setup database: {str(e)}")

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        max_time=30
    )
    async def _generate_summary(self, messages: List[Dict]) -> str:
        """Generate a summary of chat messages using Llama 3.2 3B"""
        if not messages:
            return "No messages to summarize."

        try:
            # Get or initialize Llama cog
            if not self.llama_cog:
                self.llama_cog = self.bot.get_cog('Llama32_3B')
                if not self.llama_cog:
                    logging.error("Llama32_3B cog not found")
                    return "Error: Summarization model not available."

            # Format messages for the model
            formatted_messages = []
            for msg in messages:
                speaker = "Assistant" if msg['is_assistant'] else f"User {msg['user_id']}"
                formatted_messages.append(f"{speaker}: {msg['content']}")

            conversation = "\n".join(formatted_messages)
            
            # Create a mock message object for the Llama cog
            class MockMessage:
                def __init__(self, content):
                    self.content = content
                    self.author = type('obj', (object,), {'bot': False})
                    self.channel = type('obj', (object,), {'id': 'summary'})

            mock_msg = MockMessage(
                f"Please provide a clear and concise summary (maximum 3 sentences) of this conversation:\n\n{conversation}"
            )

            # Generate summary using Llama 3.2 3B
            response_stream = await self.llama_cog.generate_response(mock_msg)
            if response_stream:
                summary = ""
                async for chunk in response_stream:
                    if chunk:
                        summary += chunk
                return summary.replace("[Llama32_3B] ", "").strip()
            else:
                return "Error generating summary."

        except Exception as e:
            logging.error(f"Failed to generate summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

    async def _check_and_create_summary(self, channel_id: str):
        """Check if we need to create a new summary and create it if necessary"""
        # Get or create lock for this channel
        if channel_id not in self.summary_locks:
            self.summary_locks[channel_id] = asyncio.Lock()

        # Use lock to prevent multiple simultaneous summaries
        async with self.summary_locks[channel_id]:
            try:
                # Check if we've recently checked this channel
                now = datetime.now()
                if channel_id in self.last_summary_check:
                    time_since_check = (now - self.last_summary_check[channel_id]).total_seconds()
                    if time_since_check < 3600:  # Don't check more than once per hour
                        return
                
                self.last_summary_check[channel_id] = now

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Get the timestamp of the last summary
                    cursor.execute("""
                        SELECT MAX(end_timestamp) FROM chat_summaries
                        WHERE channel_id = ?
                    """, (channel_id,))
                    last_summary = cursor.fetchone()[0]
                    
                    if last_summary:
                        last_summary = datetime.fromisoformat(last_summary)
                    else:
                        last_summary = datetime.now() - timedelta(hours=self.summary_chunk_hours)

                    # Get messages since last summary
                    cursor.execute("""
                        SELECT 
                            timestamp, user_id, persona_name, 
                            content, is_assistant, emotion
                        FROM messages
                        WHERE channel_id = ? AND timestamp > ?
                        ORDER BY timestamp ASC
                    """, (channel_id, last_summary.isoformat()))

                    messages = []
                    for row in cursor.fetchall():
                        messages.append({
                            'timestamp': row[0],
                            'user_id': row[1],
                            'persona_name': row[2],
                            'content': row[3],
                            'is_assistant': bool(row[4]),
                            'emotion': row[5]
                        })

                    if messages:
                        start_time = last_summary
                        end_time = datetime.fromisoformat(messages[-1]['timestamp'])
                        
                        # Only create summary if we have at least summary_chunk_hours worth of messages
                        if (end_time - start_time) >= timedelta(hours=self.summary_chunk_hours):
                            summary = await self._generate_summary(messages)
                            
                            cursor.execute("""
                                INSERT INTO chat_summaries 
                                (channel_id, start_timestamp, end_timestamp, summary)
                                VALUES (?, ?, ?, ?)
                            """, (channel_id, start_time.isoformat(), 
                                  end_time.isoformat(), summary))
                            conn.commit()
                            logging.info(f"Created new summary for channel {channel_id}")

            except Exception as e:
                logging.error(f"Failed to create summary: {str(e)}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Capture user messages to add to context"""
        if message.author.bot:
            return

        channel_id = str(message.channel.id)
        guild_id = str(message.guild.id) if message.guild else None
        user_id = str(message.author.id)
        content = message.content
        is_assistant = False
        persona_name = None
        emotion = None

        await self.add_message_to_context(channel_id, guild_id, user_id, content, 
                                        is_assistant, persona_name, emotion)
        
        # Check if we need to create a new summary
        asyncio.create_task(self._check_and_create_summary(channel_id))

    async def get_context_messages(self, channel_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation context for a channel"""
        try:
            if limit is None:
                limit = CONTEXT_WINDOWS.get(channel_id, DEFAULT_CONTEXT_WINDOW)
            
            limit = min(limit, MAX_CONTEXT_WINDOW)  # Ensure we don't exceed maximum

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get relevant summaries
                cursor.execute("""
                    SELECT summary, end_timestamp
                    FROM chat_summaries
                    WHERE channel_id = ?
                    ORDER BY end_timestamp DESC
                    LIMIT 1
                """, (channel_id,))
                summary = cursor.fetchone()

                # Return only the summary as context
                if summary:
                    return [{
                        "role": "system",
                        "content": f"Previous conversation summary: {summary['summary']}"
                    }]
                return []

        except Exception as e:
            logging.error(f"Failed to get context messages: {str(e)}")
            return []

    async def add_message_to_context(self, channel_id: str, guild_id: Optional[str], 
                                   user_id: str, content: str, is_assistant: bool,
                                   persona_name: Optional[str] = None, 
                                   emotion: Optional[str] = None) -> bool:
        """Add a new message to the conversation context"""
        try:
            timestamp = datetime.now().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (
                        channel_id, guild_id, user_id, persona_name, 
                        content, is_assistant, emotion, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (channel_id, guild_id, user_id, persona_name, 
                      content, is_assistant, emotion, timestamp))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Failed to add message to context: {str(e)}")
            return False

    async def _handle_summarize(self, channel_id: str, is_dm: bool, has_permission: bool) -> bool:
        """Common handler for summarize command logic"""
        if not is_dm and not has_permission:
            return False
            
        try:
            await self._check_and_create_summary(channel_id)
            return True
        except Exception as e:
            logging.error(f"Failed to force summarize: {str(e)}")
            return False

    @commands.command(name='summarize')
    async def summarize_command(self, ctx):
        """Force create a summary for the current channel (Legacy command)"""
        is_dm = isinstance(ctx.channel, discord.DMChannel)
        has_permission = ctx.channel.permissions_for(ctx.author).manage_messages if not is_dm else True
        
        async with ctx.typing():
            success = await self._handle_summarize(str(ctx.channel.id), is_dm, has_permission)
        
        if not success and not has_permission:
            await ctx.reply("❌ You need the Manage Messages permission to use this command.")
        elif success:
            await ctx.reply("✅ Created new chat summary")
        else:
            await ctx.reply("❌ Failed to create chat summary")

    @app_commands.command(
        name='summarize',
        description='Force create a summary for the current channel'
    )
    async def force_summarize(self, interaction: discord.Interaction):
        """Force create a summary for the current channel (Slash command)"""
        channel_id = str(interaction.channel.id)
        is_dm = isinstance(interaction.channel, discord.DMChannel)
        has_permission = interaction.channel.permissions_for(interaction.user).manage_messages if not is_dm else True
        
        if not is_dm and not has_permission:
            await interaction.response.send_message("❌ You need the Manage Messages permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer()
        success = await self._handle_summarize(channel_id, is_dm, has_permission)
        
        if success:
            await interaction.followup.send("✅ Created new chat summary")
        else:
            await interaction.followup.send("❌ Failed to create chat summary")

    @commands.command(name='getsummaries')
    async def getsummaries_command(self, ctx, hours: Optional[int] = 24):
        """Get chat summaries for this channel (Legacy command)"""
        channel_id = str(ctx.channel.id)
        try:
            async with ctx.typing():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                    
                    cursor.execute("""
                        SELECT summary, start_timestamp, end_timestamp
                        FROM chat_summaries
                        WHERE channel_id = ? AND end_timestamp > ?
                        ORDER BY end_timestamp DESC
                    """, (channel_id, cutoff_time))
                    
                    summaries = cursor.fetchall()
                    
                    if not summaries:
                        await ctx.reply("No summaries found for the specified time period.")
                        return

                    response = "📝 Chat Summaries:\n\n"
                    for summary in summaries:
                        start_time = datetime.fromisoformat(summary[1])
                        end_time = datetime.fromisoformat(summary[2])
                        response += f"From {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}:\n"
                        response += f"{summary[0]}\n\n"

                    # Split response if it's too long
                    if len(response) > 2000:
                        parts = textwrap.wrap(response, 2000)
                        for part in parts:
                            await ctx.reply(part)
                    else:
                        await ctx.reply(response)

        except Exception as e:
            logging.error(f"Failed to get summaries: {str(e)}")
            await ctx.reply("❌ Failed to retrieve chat summaries")

    @app_commands.command(
        name='getsummaries',
        description='Get chat summaries for this channel'
    )
    @app_commands.describe(hours='Number of hours to look back (default: 24)')
    async def get_summaries(self, interaction: discord.Interaction, hours: Optional[int] = 24):
        """Get chat summaries for this channel (Slash command)"""
        channel_id = str(interaction.channel.id)
        try:
            await interaction.response.defer()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                
                cursor.execute("""
                    SELECT summary, start_timestamp, end_timestamp
                    FROM chat_summaries
                    WHERE channel_id = ? AND end_timestamp > ?
                    ORDER BY end_timestamp DESC
                """, (channel_id, cutoff_time))
                
                summaries = cursor.fetchall()
                
                if not summaries:
                    await interaction.followup.send("No summaries found for the specified time period.")
                    return

                response = "📝 Chat Summaries:\n\n"
                for summary in summaries:
                    start_time = datetime.fromisoformat(summary[1])
                    end_time = datetime.fromisoformat(summary[2])
                    response += f"From {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}:\n"
                    response += f"{summary[0]}\n\n"

                # Split response if it's too long
                if len(response) > 2000:
                    parts = textwrap.wrap(response, 2000)
                    for part in parts:
                        await interaction.followup.send(part)
                else:
                    await interaction.followup.send(response)

        except Exception as e:
            logging.error(f"Failed to get summaries: {str(e)}")
            await interaction.followup.send("❌ Failed to retrieve chat summaries")

    @commands.command(name='clearsummaries')
    @commands.has_permissions(manage_messages=True)
    async def clearsummaries_command(self, ctx, hours: Optional[int] = None):
        """Clear chat summaries for this channel (Legacy command)"""
        channel_id = str(ctx.channel.id)
        is_dm = isinstance(ctx.channel, discord.DMChannel)
        has_permission = ctx.channel.permissions_for(ctx.author).manage_messages if not is_dm else True
        
        if not is_dm and not has_permission:
            await ctx.reply("❌ You need the Manage Messages permission to use this command.")
            return

        try:
            async with ctx.typing():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    if hours:
                        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                        cursor.execute("""
                            DELETE FROM chat_summaries
                            WHERE channel_id = ? AND end_timestamp < ?
                        """, (channel_id, cutoff_time))
                    else:
                        cursor.execute("""
                            DELETE FROM chat_summaries
                            WHERE channel_id = ?
                        """, (channel_id,))
                    conn.commit()

                await ctx.reply(f"🗑️ Cleared chat summaries{f' older than {hours} hours' if hours else ''}")
        except Exception as e:
            logging.error(f"Failed to clear summaries: {str(e)}")
            await ctx.reply("❌ Failed to clear chat summaries")

    @app_commands.command(
        name='clearsummaries',
        description='Clear chat summaries for this channel'
    )
    @app_commands.describe(hours='Optional: Clear summaries older than this many hours')
    async def clear_summaries(self, interaction: discord.Interaction, hours: Optional[int] = None):
        """Clear chat summaries for this channel (Slash command)"""
        channel_id = str(interaction.channel.id)
        is_dm = isinstance(interaction.channel, discord.DMChannel)
        has_permission = interaction.channel.permissions_for(interaction.user).manage_messages if not is_dm else True
        
        if not is_dm and not has_permission:
            await interaction.response.send_message("❌ You need the Manage Messages permission to use this command.", ephemeral=True)
            return

        try:
            await interaction.response.defer()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if hours:
                    cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                    cursor.execute("""
                        DELETE FROM chat_summaries
                        WHERE channel_id = ? AND end_timestamp < ?
                    """, (channel_id, cutoff_time))
                else:
                    cursor.execute("""
                        DELETE FROM chat_summaries
                        WHERE channel_id = ?
                    """, (channel_id,))
                conn.commit()

                await interaction.followup.send(f"🗑️ Cleared chat summaries{f' older than {hours} hours' if hours else ''}")
        except Exception as e:
            logging.error(f"Failed to clear summaries: {str(e)}")
            await interaction.followup.send("❌ Failed to clear chat summaries")

async def setup(bot):
    await bot.add_cog(ContextCog(bot))
