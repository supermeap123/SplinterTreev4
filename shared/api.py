import os
import logging
import time
import json
import asyncio
import sqlite3
import base64
from typing import Dict, Any, List, Union, AsyncGenerator
import aiohttp
import backoff
from urllib.parse import urlparse, urljoin
from config import OPENPIPE_API_KEY, OPENROUTER_API_KEY, OPENPIPE_API_URL
from openai import AsyncOpenAI

class API:
    def __init__(self):
        # Initialize aiohttp session
        self.session = aiohttp.ClientSession()
        
        # Initialize OpenPipe client
        self.openpipe_client = AsyncOpenAI(
            api_key=OPENPIPE_API_KEY,
            base_url=OPENPIPE_API_URL  # Base URL already includes /api/v1
        )

        # Initialize OpenRouter client
        self.openrouter_client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )

        # Connect to SQLite database and apply schema
        try:
            # Ensure the databases directory exists
            os.makedirs('databases', exist_ok=True)
            
            # Connect to the database
            self.db_conn = sqlite3.connect('databases/interaction_logs.db')
            self.db_cursor = self.db_conn.cursor()
            
            # Apply schema
            self._apply_schema()
            logging.info("[API] Connected to database and applied schema")
        except Exception as e:
            logging.error(f"[API] Failed to connect to database or apply schema: {str(e)}")
            self.db_conn = None
            self.db_cursor = None

    def _apply_schema(self):
        """Apply database schema"""
        try:
            with open('databases/schema.sql', 'r') as schema_file:
                schema_sql = schema_file.read()
            
            # Split SQL statements and execute each separately
            statements = schema_sql.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement:
                    self.db_cursor.execute(statement)
            
            self.db_conn.commit()
            logging.info("[API] Successfully applied database schema")
        except Exception as e:
            logging.error(f"[API] Failed to apply database schema: {str(e)}")
            raise

    async def _download_image(self, url: str) -> bytes:
        """Download image from URL"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logging.error(f"[API] Failed to download image. Status code: {response.status}")
                    return None
        except Exception as e:
            logging.error(f"[API] Error downloading image: {str(e)}")
            return None

    async def _convert_image_to_base64(self, url: str) -> str:
        """Convert image URL to base64"""
        try:
            image_data = await self._download_image(url)
            if image_data:
                # Detect MIME type based on image data
                mime_type = self._detect_mime_type(image_data)
                base64_image = base64.b64encode(image_data).decode('utf-8')
                return f"data:{mime_type};base64,{base64_image}"
            return None
        except Exception as e:
            logging.error(f"[API] Error converting image to base64: {str(e)}")
            return None

    def _detect_mime_type(self, image_data: bytes) -> str:
        """Detect MIME type of image data"""
        # Common image signatures
        signatures = {
            b'\xFF\xD8\xFF': 'image/jpeg',
            b'\x89PNG\r\n\x1a\n': 'image/png',
            b'GIF87a': 'image/gif',
            b'GIF89a': 'image/gif',
            b'RIFF': 'image/webp'
        }
        
        for signature, mime_type in signatures.items():
            if image_data.startswith(signature):
                return mime_type
        
        return 'application/octet-stream'  # Default fallback

    async def _validate_message_roles(self, messages: List[Dict]) -> List[Dict]:
        """Validate and normalize message roles for API compatibility"""
        valid_roles = {"system", "user", "assistant"}
        normalized_messages = []
        
        for msg in messages:
            role = msg.get('role', '').lower()
            
            # Skip messages with invalid roles
            if role not in valid_roles:
                logging.warning(f"[API] Skipping message with invalid role: {role}")
                continue
            
            # Create normalized message
            normalized_msg = {
                "role": role,
                "content": msg.get('content', '')
            }
            
            # Handle multimodal content
            if isinstance(normalized_msg['content'], list):
                # Verify and convert image URLs to base64
                valid_content = []
                for item in normalized_msg['content']:
                    if isinstance(item, dict) and 'type' in item:
                        if item['type'] == 'text' and 'text' in item:
                            valid_content.append(item)
                        elif item['type'] == 'image_url' and 'image_url' in item:
                            # Convert image URL to base64 with proper awaiting
                            base64_image = await self._convert_image_to_base64(item['image_url'])
                            if base64_image:
                                valid_content.append({
                                    "type": "image_url",
                                    "image_url": base64_image
                                })
                normalized_msg['content'] = valid_content
            
            normalized_messages.append(normalized_msg)
        
        return normalized_messages

    # Rest of the code remains the same as in the previous implementation
    # ... (previous _stream_openrouter_request, call_openrouter, etc. methods)

    async def close(self):
        await self.session.close()
        if self.db_conn:
            self.db_conn.close()

api = API()
