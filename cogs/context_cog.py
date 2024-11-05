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

from llama32_90b_cog import Llama3290bVisionCog


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
        self.llama_cog = Llama3290bVisionCog(bot)

    def _setup_database(self):
        """Ensure database and tables exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load and execute schema if needed
                with open('databases/schema.sql', 'r') as f:
                    conn.executescript(f.read())
        except Exception as e:
            logging.error(f"Failed to setup database: {str(e)}")

    async def _generate_summary(self, messages: List[Dict]) -> str:
        """Generate a summary of chat messages using OpenAI/OpenPipe"""
        # ... (Existing implementation from the read_file output)

    # ... (The rest of the methods from the read_file output, unchanged)

    async def get_alt_text(self, message: discord.Message) -> Optional[str]:
        """Retrieves alternative text from image attachments or generates a description using Llama 3.2 90b vision instruct."""
        return await self.llama_cog.get_alt_text(message)


async def setup(bot):
    await bot.add_cog(ContextCog(bot))
