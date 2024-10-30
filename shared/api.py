import os
import logging
import time
import json
import asyncio
import sqlite3
from typing import Dict, Any, List, Union
from openai import OpenAI
import backoff
import httpx
from functools import partial
from config import OPENPIPE_API_URL, OPENPIPE_API_KEY

class API:
    def __init__(self):
        # Configure httpx client with timeouts and limits
        self.timeout = httpx.Timeout(
            connect=10.0,  # Connection timeout
            read=30.0,     # Read timeout
            write=10.0,    # Write timeout
            pool=5.0       # Pool timeout
        )
        self.limits = httpx.Limits(
            max_keepalive_connections=5,
            max_connections=10,
            keepalive_expiry=30.0
        )
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=OPENPIPE_API_KEY, base_url=OPENPIPE_API_URL, timeout=self.timeout)
        logging.info("[API] Initialized with OpenPipe configuration")

        # Connect to SQLite database
        self.db_conn = sqlite3.connect('databases/interaction_logs.db')
        self.db_cursor = self.db_conn.cursor()

    def _make_openrouter_request(self, messages, model, temperature, max_tokens):
        """Synchronous OpenRouter API call"""
        logging.debug(f"[API] Making OpenRouter request to model: {model}")
        logging.debug(f"[API] Temperature: {temperature}, Max tokens: {max_tokens}")
        
        requested_at = int(time.time() * 1000)
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
        received_at = int(time.time() * 1000)

        # Process stream synchronously
        full_response = ""
        for chunk in completion:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content

        # Create completion object for reporting
        completion_obj = {
            'choices': [{
                'message': {
                    'content': full_response
                }
            }]
        }

        # Log request to database
        self.report(
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

        return full_response

    @backoff.on_exception(
        backoff.expo,
        (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout),
        max_tries=3,
        max_time=30
    )
    async def call_openrouter(self, messages: List[Dict[str, Union[str, List[Dict[str, Any]]]]], model: str, temperature: float = None):
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

                # Run API call in thread pool
                loop = asyncio.get_event_loop()
                full_response = await loop.run_in_executor(
                    None,
                    partial(self._make_openrouter_request, messages, full_model, temperature, max_tokens)
                )

                # Convert to dict format for consistency
                response_dict = {
                    'choices': [{
                        'message': {
                            'content': full_response
                        }
                    }]
                }
                logging.debug("[API] Successfully received OpenRouter response")
                return response_dict

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
            else:
                logging.error(f"[API] OpenRouter error: {error_message}")
                raise Exception(f"OpenRouter API error: {error_message}")

    @backoff.on_exception(
        backoff.expo,
        (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout),
        max_tries=3,
        max_time=30
    )
    async def call_openpipe(self, messages: List[Dict[str, Union[str, List[Dict[str, Any]]]]], model: str, temperature: float = 0.7):
        try:
            logging.debug(f"[API] Making OpenPipe request to model: {model}")
            logging.debug(f"[API] Request messages structure:")
            for msg in messages:
                logging.debug(f"[API] Message role: {msg.get('role')}")
                logging.debug(f"[API] Message content: {msg.get('content')}")

            try:
                # Ensure temperature is not None
                if temperature is None:
                    temperature = 1

                requested_at = int(time.time() * 1000)
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=1000,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                    stream=True
                )
                
                # Process stream synchronously
                full_response = ""
                for chunk in completion:
                    if hasattr(chunk.choices[0].delta, 'content'):
                        content = chunk.choices[0].delta.content
                        if content:
                            full_response += content

                received_at = int(time.time() * 1000)

                # Create completion object for reporting
                completion_obj = {
                    'choices': [{
                        'message': {
                            'content': full_response
                        }
                    }]
                }

                # Log request to database
                self.report(
                    requested_at=requested_at,
                    received_at=received_at,
                    req_payload={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 1000
                    },
                    resp_payload=completion_obj,
                    status_code=200,
                    tags={"source": "openpipe"}
                )

                # Return response dict
                response_dict = {
                    'choices': [{
                        'message': {
                            'content': full_response
                        }
                    }]
                }
                logging.debug("[API] Successfully received OpenPipe response")
                return response_dict

            except Exception as e:
                logging.error(f"[API] OpenPipe request error: {str(e)}")
                raise

        except Exception as e:
            error_message = str(e)
            if "invalid_api_key" in error_message.lower():
                logging.error("[API] Invalid OpenPipe API key")
                raise Exception("🔑 Invalid OpenPipe API key. Please check your configuration.")
            elif "insufficient_quota" in error_message.lower():
                logging.error("[API] OpenPipe quota exceeded")
                raise Exception("⚠️ OpenPipe quota exceeded. Please check your subscription.")
            elif "rate_limit_exceeded" in error_message.lower():
                logging.error("[API] OpenPipe rate limit exceeded")
                raise Exception("⏳ Rate limit exceeded. Please try again later.")
            else:
                logging.error(f"[API] OpenPipe error: {error_message}")
                raise Exception(f"OpenPipe API error: {error_message}")

    async def report(self, requested_at: int, received_at: int, req_payload: Dict, resp_payload: Dict, status_code: int, tags: Dict = None):
        """Report interaction metrics"""
        try:
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

    def __del__(self):
        # Close database connection
        self.db_conn.close()

api = API()
