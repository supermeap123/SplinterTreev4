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
from config import OPENPIPE_API_KEY, OPENPIPE_API_URL
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

        # Rate limiting
        self.rate_limit_lock = asyncio.Lock()
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

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
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logging.error(f"[API] Failed to download image. Status code: {response.status}")
                    return None
        except asyncio.TimeoutError:
            logging.error("[API] Image download timed out")
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

    def _get_prefixed_model(self, model: str, provider: str = None) -> str:
        """Get the appropriate model name with prefix based on provider"""
        # Remove 'openpipe:' prefix
        model = model.replace('openpipe:', '')
        
        # If provider is specified, add the prefix
        if provider == 'openpipe':
            return model
        elif provider == 'openrouter':
            return f"openrouter:{model}"
        
        return model

    async def _stream_openpipe_request(self, messages, model, temperature, max_tokens, provider=None, user_id=None, guild_id=None, prompt_file=None):
        """Stream responses from OpenPipe API"""
        logging.debug(f"[API] Making OpenPipe streaming request to model: {model}")
        
        try:
            # Enforce rate limit
            await self._enforce_rate_limit()
            
            # Get prefixed model name
            openpipe_model = self._get_prefixed_model(model, provider)
            
            # Validate and normalize message roles
            validated_messages = await self._validate_message_roles(messages)
            
            stream = await self.openpipe_client.chat.completions.create(
                model=openpipe_model,
                messages=validated_messages,
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens if max_tokens is not None else 1000,
                stream=True,
                store=True
            )
            requested_at = int(time.time() * 1000)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            received_at = int(time.time() * 1000)

            # Prepare tags with all metadata
            tags = {
                "source": "openpipe",
                "user_id": str(user_id) if user_id else None,
                "guild_id": str(guild_id) if guild_id else None,
                "prompt_file": prompt_file
            }

            # Log request to database after completion
            completion_obj = {
                'choices': [{
                    'message': {
                        'content': "Streaming response completed"
                    }
                }]
            }
            await self.report(
                requested_at=requested_at,
                received_at=received_at,
                req_payload={
                    "model": openpipe_model,
                    "messages": validated_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                resp_payload=completion_obj,
                status_code=200,
                tags=tags,
                user_id=user_id,
                guild_id=guild_id
            )
        except Exception as e:
            error_message = str(e)
            logging.error(f"[API] OpenPipe streaming error: {error_message}")
            raise Exception(f"OpenPipe API error: {error_message}")

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=5,
        max_time=60
    )
    async def call_openpipe(self, messages: List[Dict[str, Union[str, List[Dict[str, Any]]]]], model: str, temperature: float = None, stream: bool = False, max_tokens: int = None, provider: str = None, user_id: str = None, guild_id: str = None, prompt_file: str = None) -> Union[Dict, AsyncGenerator[str, None]]:
        try:
            # Enforce rate limit
            await self._enforce_rate_limit()
            
            # Get prefixed model name
            openpipe_model = self._get_prefixed_model(model, provider)
            
            logging.debug(f"[API] Making OpenPipe request to model: {openpipe_model}")
            logging.debug(f"[API] Request messages structure:")
            for msg in messages:
                logging.debug(f"[API] Message role: {msg.get('role')}")
                logging.debug(f"[API] Message content: {msg.get('content')}")

            if stream:
                return self._stream_openpipe_request(messages, model, temperature, max_tokens, provider, user_id, guild_id, prompt_file)
            else:
                # Validate and normalize message roles
                validated_messages = await self._validate_message_roles(messages)
                
                requested_at = int(time.time() * 1000)
                response = await self.openpipe_client.chat.completions.create(
                    model=openpipe_model,
                    messages=validated_messages,
                    temperature=temperature if temperature is not None else 0.7,
                    max_tokens=max_tokens if max_tokens is not None else 1000,
                    store=True
                )
                received_at = int(time.time() * 1000)

                result = {
                    'choices': [{
                        'message': {
                            'content': response.choices[0].message.content
                        }
                    }]
                }

                # Prepare tags with all metadata
                tags = {
                    "source": "openpipe",
                    "user_id": str(user_id) if user_id else None,
                    "guild_id": str(guild_id) if guild_id else None,
                    "prompt_file": prompt_file
                }

                # Log the interaction
                await self.report(
                    requested_at=requested_at,
                    received_at=received_at,
                    req_payload={
                        "model": openpipe_model,
                        "messages": validated_messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    resp_payload=result,
                    status_code=200,
                    tags=tags,
                    user_id=user_id,
                    guild_id=guild_id
                )

                return result

        except Exception as e:
            error_message = str(e)
            logging.error(f"[API] OpenPipe error: {error_message}")
            raise Exception(f"OpenPipe API error: {error_message}")

    # Alias for OpenRouter models to use OpenPipe
    async def call_openrouter(self, messages: List[Dict[str, Union[str, List[Dict[str, Any]]]]], model: str, temperature: float = None, stream: bool = False, max_tokens: int = None, user_id: str = None, guild_id: str = None, prompt_file: str = None) -> Union[Dict, AsyncGenerator[str, None]]:
        """Redirect OpenRouter calls to OpenPipe with 'openrouter' provider"""
        return await self.call_openpipe(
            messages=messages, 
            model=model, 
            temperature=temperature, 
            stream=stream, 
            max_tokens=max_tokens, 
            provider='openrouter',
            user_id=user_id,
            guild_id=guild_id,
            prompt_file=prompt_file
        )

    async def report(self, requested_at: int, received_at: int, req_payload: Dict, resp_payload: Dict, status_code: int, tags: Dict = None, user_id: str = None, guild_id: str = None):
        """Report interaction metrics"""
        try:
            if self.db_conn is None or self.db_cursor is None:
                logging.error("[API] Database connection not available. Skipping logging.")
                return

            # Add timestamp to tags
            if tags is None:
                tags = {}
            tags_str = json.dumps(tags)

            # Prepare SQL statement
            sql = """
                INSERT INTO logs (
                    requested_at, received_at, request, response, 
                    status_code, tags, user_id, guild_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            values = (
                requested_at, received_at, json.dumps(req_payload),
                json.dumps(resp_payload), status_code, tags_str,
                user_id, guild_id
            )

            # Execute SQL statement
            self.db_cursor.execute(sql, values)
            self.db_conn.commit()
            logging.debug(f"[API] Logged interaction with status code {status_code}")

        except Exception as e:
            logging.error(f"[API] Failed to report interaction: {str(e)}")

    async def close(self):
        await self.session.close()
        if self.db_conn:
            self.db_conn.close()

api = API()
