import os
import logging
import time
import json
import asyncio
import sqlite3
from typing import Dict, Any, List, Union, AsyncGenerator
from openai import OpenAI
import backoff
import httpx
from functools import partial
from config import OPENPIPE_API_URL, OPENPIPE_API_KEY, OPENAI_API_KEY

class API:
    def __init__(self):
        # Configure httpx client with timeouts and limits
        self.timeout = httpx.Timeout(
            connect=15.0,  # Increased connection timeout
            read=60.0,     # Increased read timeout
            write=15.0,    # Increased write timeout
            pool=10.0      # Increased pool timeout
        )
        self.limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
            keepalive_expiry=60.0
        )
        
        # Initialize OpenAI client with OPENAI_API_KEY
        self.client = OpenAI(api_key=OPENAI_API_KEY, timeout=self.timeout)
        logging.info("[API] Initialized with OpenAI configuration")

        # Initialize OpenPipe client
        self.openpipe_client = OpenAI(api_key=OPENPIPE_API_KEY, base_url=OPENPIPE_API_URL, timeout=self.timeout)
        logging.info("[API] Initialized with OpenPipe configuration")

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
        """Asynchronous OpenRouter API streaming call"""
        logging.debug(f"[API] Making OpenRouter streaming request to model: {model}")
        logging.debug(f"[API] Temperature: {temperature}, Max tokens: {max_tokens}")
        
        requested_at = int(time.time() * 1000)
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature if temperature is not None else 1,
                max_tokens=max_tokens,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stream=True
            )

            full_response = ""
            for chunk in completion:
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                        yield content

            received_at = int(time.time() * 1000)

            # Log request to database after completion
            completion_obj = {
                'choices': [{
                    'message': {
                        'content': full_response
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
            logging.error(f"[API] Error in _stream_openrouter_request: {str(e)}")
            raise

    @backoff.on_exception(
        backoff.expo,
        (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout, ConnectionError),
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

            # Handle model name prefixing
            if model.startswith('openpipe:'):
                full_model = model
            else:
                full_model = f"openpipe:openrouter/{model}"
            logging.debug(f"[API] Using model: {full_model}")

            try:
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
                    return self._stream_openrouter_request(messages, full_model, temperature, max_tokens)
                else:
                    # Collect all chunks for non-streaming response
                    full_response = ""
                    async for chunk in self._stream_openrouter_request(messages, full_model, temperature, max_tokens):
                        full_response += chunk

                    return {
                        'choices': [{
                            'message': {
                                'content': full_response
                            }
                        }]
                    }

            except Exception as e:
                logging.error(f"[API] OpenRouter request error: {str(e)}")
                raise

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
            elif isinstance(e, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout, ConnectionError)):
                logging.error(f"[API] Connection error: {str(e)}")
                raise Exception("🌐 Connection error. Please check your internet connection and try again.")
            else:
                logging.error(f"[API] OpenRouter error: {error_message}")
                raise Exception(f"OpenRouter API error: {error_message}")

    # ... (rest of the code remains unchanged)

api = API()
