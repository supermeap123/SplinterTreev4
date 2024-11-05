import discord
from discord.ext import commands
from config import CONTEXT_WINDOWS, DEFAULT_CONTEXT_WINDOW, MAX_CONTEXT_WINDOW, OPENPIPE_API_KEY, OPENPIPE_API_URL
import sqlite3
import json
import logging
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional
import textwrap
from openai import OpenAI

class ContextCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'databases/interaction_logs.db'
        self._setup_database()
        self.summary_chunk_hours = 24  # Summarize every 24 hours of chat
        self.last_summary_check = {}  # Track last summary generation per channel
        self.openai_client = OpenAI(
            base_url=OPENPIPE_API_URL,
            api_key=OPENPIPE_API_KEY
        )
        # Track processed message IDs to prevent duplicates
        self.processed_messages = set()

    def _setup_database(self):
        """Ensure database and tables exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load and execute schema if needed
                with open('databases/schema.sql', 'r') as f:
                    conn.executescript(f.read())
        except Exception as e:
            logging.error(f"Failed to setup database: {str(e)}")

    async def get_alt_text(self, message: discord.Message) -> Optional[str]:
        """Retrieves alternative text from image attachments or generates a description using Llama 3.2 90b vision instruct."""
        try:
            llama_cog = self.bot.get_cog('Llama-3.2-90B-Vision')
            if llama_cog:
                return await llama_cog.get_alt_text(message)
            return None
        except Exception as e:
            logging.error(f"Error getting alt text: {str(e)}")
            return None

    async def _generate_summary(self, messages: List[Dict]) -> str:
        """Generate a summary of chat messages using OpenAI/OpenPipe"""
        if not messages:
            return "No messages to summarize."

        try:
            # Format messages for the API with proper roles
            formatted_messages = []
            
            # Add system prompt
            formatted_messages.append({
                "role": "system",
                "content": "You are a helpful assistant that summarizes Discord chat conversations. Create a concise summary that captures the main points and key interactions of the conversation. Focus on the important topics discussed and any decisions or conclusions reached."
            })
            
            # Format conversation messages
            conversation_text = []
            for msg in messages:
                speaker = "Assistant" if msg['is_assistant'] else f"User {msg['user_id']}"
                conversation_text.append(f"{speaker}: {msg['content']}")
            
            # Add conversation as user message
            formatted_messages.append({
                "role": "user",
                "content": f"Please summarize this conversation:\n\n{chr(10).join(conversation_text)}"
            })
            
            # Make API call
            completion = await self.openai_client.chat.completions.acreate(
                model="openpipe:moa-gpt-4o-v1",
                messages=formatted_messages,
                store=True,
                metadata={"type": "discord_summary"}
            )

            summary = completion.choices[0].message.content
            return summary

        except Exception as e:
            logging.error(f"Failed to generate summary: {str(e)}")
            return "Error generating summary."

    async def _check_and_create_summary(self, channel_id: str):
        """Check if we need to create a new summary and create it if necessary"""
        try:
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

        except Exception as e:
            logging.error(f"Failed to create summary: {str(e)}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Capture user messages to add to context"""
        if message.author.bot:
            return

        # Skip if message has already been processed
        if str(message.id) in self.processed_messages:
            return

        # Only process messages that aren't triggering any cogs
        msg_content = message.content.lower()
        for cog in self.bot.cogs.values():
            if hasattr(cog, 'trigger_words'):
                if any(word in msg_content for word in cog.trigger_words):
                    return  # Skip processing as this will be handled by the triggered cog

        channel_id = str(message.channel.id)
        guild_id = str(message.guild.id) if message.guild else None
        user_id = str(message.author.id)
        content = message.content
        
        # Add alt text from attachments/embeds if present
        alt_text = await self.get_alt_text(message)
        if alt_text:
            content = f"{content}\n{alt_text}"
            
        is_assistant = False
        persona_name = None
        emotion = None

        await self.add_message_to_context(message.id, channel_id, guild_id, user_id, content, 
                                        is_assistant, persona_name, emotion)
        
        # Check if we need to create a new summary
        await self._check_and_create_summary(channel_id)

    async def get_context_messages(self, channel_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation context for a channel"""
        try:
            # Use channel-specific context window or default
            if limit is None:
                limit = CONTEXT_WINDOWS.get(channel_id, DEFAULT_CONTEXT_WINDOW)
            
            # Ensure limit doesn't exceed maximum
            limit = min(limit, MAX_CONTEXT_WINDOW)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get summaries
                cursor.execute("""
                    SELECT summary, end_timestamp
                    FROM chat_summaries
                    WHERE channel_id = ?
                    ORDER BY end_timestamp DESC
                """, (channel_id,))
                summaries = cursor.fetchall()

                # Get recent messages using the configured limit
                cursor.execute("""
                    SELECT 
                        timestamp,
                        user_id,
                        persona_name,
                        content,
                        is_assistant,
                        emotion
                    FROM messages
                    WHERE channel_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (channel_id, limit))

                recent_messages = []
                for row in cursor.fetchall():
                    recent_messages.append({
                        'timestamp': row['timestamp'],
                        'user_id': row['user_id'],
                        'persona_name': row['persona_name'],
                        'content': row['content'],
                        'is_assistant': bool(row['is_assistant']),
                        'emotion': row['emotion']
                    })

                # Combine summaries and recent messages
                context = []
                
                # Add summaries first
                for summary in summaries:
                    context.append({
                        'timestamp': summary['end_timestamp'],
                        'user_id': 'SYSTEM',
                        'persona_name': None,
                        'content': f"[SUMMARY] {summary['summary']}",
                        'is_assistant': False,
                        'emotion': None
                    })

                # Add recent messages in chronological order
                context.extend(reversed(recent_messages))

                return context

        except Exception as e:
            logging.error(f"Failed to get context messages: {str(e)}")
            return []

    async def add_message_to_context(self, discord_message_id: int, channel_id: str, guild_id: Optional[str], 
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
                        discord_message_id, channel_id, guild_id, user_id, persona_name, 
                        content, is_assistant, emotion, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(discord_message_id), channel_id, guild_id, user_id, persona_name, 
                      content, is_assistant, emotion, timestamp))
                conn.commit()
                # Add to processed messages set
                self.processed_messages.add(str(discord_message_id))
                return True
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logging.debug(f"Message {discord_message_id} already exists in database")
                return True
            logging.error(f"Database integrity error: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Failed to add message to context: {str(e)}")
            return False

    @commands.command(name='summarize')
    @commands.has_permissions(manage_messages=True)
    async def force_summarize(self, ctx):
        """Force create a summary for the current channel"""
        channel_id = str(ctx.channel.id)
        try:
            await self._check_and_create_summary(channel_id)
            await ctx.reply("✅ Created new chat summary")
        except Exception as e:
            logging.error(f"Failed to force summarize: {str(e)}")
            await ctx.reply("❌ Failed to create chat summary")

    @commands.command(name='getsummaries')
    async def get_summaries(self, ctx, hours: Optional[int] = 24):
        """Get chat summaries for this channel"""
        channel_id = str(ctx.channel.id)
        try:
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

    @commands.command(name='clearsummaries')
    @commands.has_permissions(manage_messages=True)
    async def clear_summaries(self, ctx, hours: Optional[int] = None):
        """Clear chat summaries for this channel"""
        channel_id = str(ctx.channel.id)
        try:
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

async def setup(bot):
    await bot.add_cog(ContextCog(bot))
