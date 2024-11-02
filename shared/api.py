import os
import logging
import time
import json
import asyncio
import sqlite3
from typing import Dict, Any, List, Union, AsyncGenerator
import aiohttp
import backoff
from urllib.parse import urlparse, urljoin
from config import OPENPIPE_API_KEY, OPENROUTER_API_KEY, OPENPIPE_API_URL
from openpipe import AsyncOpenAI as OpenPipeAI

class API:
    def __init__(self):
        # Initialize aiohttp session
        self.session = aiohttp.ClientSession()
        
        # Initialize OpenPipe client for both OpenPipe and OpenRouter
        self.client = OpenPipeAI(
            api_key=OPENPIPE_API_KEY,
            openpipe={
                "api_key": OPENPIPE_API_KEY,
                "base_url": OPENPIPE_API_URL
            }
        )

        # Connect to SQLite database and apply schema
        try:
            self.db_conn = sqlite3.connect('databases/interaction_logs.db')
            self.db_cursor = self.db_conn.cursor()
            self._apply_schema()
            logging.info("[API] Connected to database and applied schema")
        except Exception as e:
            logging.error(f"[API] Failed to connect to database or apply schema: {str(e)}")
            self.db_conn = None
            self.db_cursor = None

    def _apply_schema(self):
        try:
            with open('databases/schema.sql', 'r') as schema_file:
                schema_sql = schema_file.read()
            self.db_cursor.executescript(schema_sql)
            self.db_conn.commit()
            logging.info("[API] Successfully applied database schema")
        except Exception as e:
            logging.error(f"[API] Failed to apply database schema: {str(e)}")
            raise

    async def _stream_openrouter_request(self, messages, model, temperature, max_tokens):
        """Stream responses from OpenRouter API"""
        logging.debug(f"[API] Making OpenRouter streaming request to model: {model}")
        logging.debug(f"[API] Request messages: {json.dumps(messages, indent=2)}")
        logging.debug(f"[API] Temperature: {temperature}, Max tokens: {max_tokens}")
        
        try:
            # Create a new client instance with OpenRouter configuration
            openrouter_client = OpenPipeAI(
                api_key=OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            
            # Log the full request details
            request_data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
            logging.info(f"[API] OpenRouter request data: {json.dumps(request_data, indent=2)}")
            
            stream = await openrouter_client.chat.completions.create(**request_data)
            requested_at = int(time.time() * 1000)
            
            # Track if we've received any content
            has_content = False
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    has_content = True
                    yield chunk.choices[0].delta.content

            received_at = int(time.time() * 1000)

            if not has_content:
                logging.error(f"[API] OpenRouter stream completed but no content was received for model {model}")
                return None

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
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                resp_payload=completion_obj,
                status_code=200,
                tags={"source": "openrouter"}
            )
        except Exception as e:
            error_message = str(e)
            logging.error(f"[API] OpenRouter streaming error for model {model}: {error_message}")
            logging.error(f"[API] Full request data that caused error: {json.dumps(request_data, indent=2)}")
            raise Exception(f"OpenRouter API error: {error_message}")

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=5,
        max_time=60
    )
    async def call_openrouter(self, messages: List[Dict[str, Union[str, List[Dict[str, Any]]]]], model: str, temperature: float = None, stream: bool = False) -> Union[Dict, AsyncGenerator[str, None]]:
        try:
            # Check if any message contains vision content
            has_vision_content = any(
                isinstance(msg.get('content'), list) and 
                any(content.get('type') == 'image_url' for content in msg['content'])
                for msg in messages
            )
            logging.debug(f"[API] Message contains vision content: {has_vision_content}")

            # Configure parameters based on content type
            max_tokens = 2000 if has_vision_content else 1000
            
            # Use provided temperature or default based on content type
            if temperature is None:
                temperature = 0.5 if has_vision_content else 0.7
            logging.debug(f"[API] Using max_tokens={max_tokens}, temperature={temperature}")

            # Log request details
            logging.debug(f"[API] OpenRouter request messages structure:")
            for msg in messages:
                if isinstance(msg.get('content'), list):
                    logging.debug(f"[API] Message type: multimodal")
                    text_parts = [c['text'] for c in msg['content'] if c['type'] == 'text']
                    image_parts = [c for c in msg['content'] if c['type'] == 'image_url']
                    logging.debug(f"[API] Text parts: {text_parts}")
                    logging.debug(f"[API] Number of images: {len(image_parts)}")
                else:
                    logging.debug(f"[API] Message type: text")
                    logging.debug(f"[API] Content: {msg.get('content')}")

            if stream:
                return self._stream_openrouter_request(messages, model, temperature, max_tokens)
            else:
                # Create a new client instance with OpenRouter configuration
                openrouter_client = OpenPipeAI(
                    api_key=OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1"
                )
                
                # Log the full request details
                request_data = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                logging.info(f"[API] OpenRouter non-streaming request data: {json.dumps(request_data, indent=2)}")
                
                # Non-streaming request
                requested_at = int(time.time() * 1000)
                response = await openrouter_client.chat.completions.create(**request_data)
                received_at = int(time.time() * 1000)

                result = {
                    'choices': [{
                        'message': {
                            'content': response.choices[0].message.content
                        }
                    }]
                }

                # Log the interaction
                await self.report(
                    requested_at=requested_at,
                    received_at=received_at,
                    req_payload=request_data,
                    resp_payload=result,
                    status_code=200,
                    tags={"source": "openrouter"}
                )

                return result

        except Exception as e:
            error_message = str(e)
            if "insufficient_quota" in error_message.lower():
                logging.error("[API] OpenRouter credits depleted")
                raise Exception("⚠️ OpenRouter credits depleted. Please visit https://openrouter.ai/credits to add more.")
            elif "invalid_api_key" in error_message.lower():
                logging.error("[API] Invalid OpenRouter API key")
                raise Exception("🔑 Invalid OpenRouter API key. Please check your configuration.")
            elif "rate_limit_exceeded" in error_message.lower():
                logging.error("[API] OpenRouter rate limit exceeded")
                raise Exception("⏳ Rate limit exceeded. Please try again later.")
            elif isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)):
                logging.error(f"[API] Connection error: {str(e)}")
                raise Exception("🌐 Connection error. Please check your internet connection and try again.")
            else:
                logging.error(f"[API] OpenRouter error: {error_message}")
                raise Exception(f"OpenRouter API error: {error_message}")

    async def _stream_openpipe_request(self, messages, model, temperature, max_tokens):
        """Stream responses from OpenPipe API"""
        logging.debug(f"[API] Making OpenPipe streaming request to model: {model}")
        logging.debug(f"[API] Request messages: {json.dumps(messages, indent=2)}")
        logging.debug(f"[API] Temperature: {temperature}, Max tokens: {max_tokens}")
        
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens if max_tokens is not None else 1000,
                stream=True
            )
            requested_at = int(time.time() * 1000)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            received_at = int(time.time() * 1000)

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
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                resp_payload=completion_obj,
                status_code=200,
                tags={"source": "openpipe"}
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
    async def call_openpipe(self, messages: List[Dict[str, Union[str, List[Dict[str, Any]]]]], model: str, temperature: float = None, stream: bool = False, max_tokens: int = None) -> Union[Dict, AsyncGenerator[str, None]]:
        try:
            logging.debug(f"[API] Making OpenPipe request to model: {model}")
            logging.debug(f"[API] Request messages: {json.dumps(messages, indent=2)}")
            logging.debug(f"[API] Temperature: {temperature}, Max tokens: {max_tokens}, Stream: {stream}")

            if stream:
                return self._stream_openpipe_request(messages, model, temperature, max_tokens)
            else:
                requested_at = int(time.time() * 1000)
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature if temperature is not None else 0.7,
                    max_tokens=max_tokens if max_tokens is not None else 1000
                )
                received_at = int(time.time() * 1000)

                result = {
                    'choices': [{
                        'message': {
                            'content': response.choices[0].message.content
                        }
                    }]
                }

                # Log the interaction
                await self.report(
                    requested_at=requested_at,
                    received_at=received_at,
                    req_payload={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    resp_payload=result,
                    status_code=200,
                    tags={"source": "openpipe"}
                )

                return result

        except Exception as e:
            error_message = str(e)
            logging.error(f"[API] OpenPipe error: {error_message}")
            raise Exception(f"OpenPipe API error: {error_message}")

    async def report(self, requested_at: int, received_at: int, req_payload: Dict, resp_payload: Dict, status_code: int, tags: Dict = None):
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
            sql = "INSERT INTO logs (requested_at, received_at, request, response, status_code, tags) VALUES (?, ?, ?, ?, ?, ?)"
            values = (requested_at, received_at, json.dumps(req_payload), json.dumps(resp_payload), status_code, tags_str)

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
