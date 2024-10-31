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
from config import OPENPIPE_API_URL, OPENPIPE_API_KEY, OPENROUTER_API_KEY

class API:
    def __init__(self):
        # Initialize aiohttp session
        self.session = aiohttp.ClientSession()
        
        # Initialize OpenPipe client
        try:
            parsed_url = urlparse(OPENPIPE_API_URL)
            self.openpipe_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            self.openpipe_path = parsed_url.path
            logging.info(f"[API] Initialized with OpenPipe base URL: {self.openpipe_base_url}")
            logging.info(f"[API] OpenPipe path: {self.openpipe_path}")
        except Exception as e:
            logging.error(f"[API] Failed to parse OpenPipe API URL: {str(e)}")
            self.openpipe_base_url = None
            self.openpipe_path = None

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
        """Asynchronous OpenRouter API streaming call using direct HTTP request"""
        logging.debug(f"[API] Making OpenRouter streaming request to model: {model}")
        logging.debug(f"[API] Temperature: {temperature}, Max tokens: {max_tokens}")
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else 1,
            "max_tokens": max_tokens,
            "stream": True
        }

        requested_at = int(time.time() * 1000)
        async with self.session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                error_text = await response.text()
                logging.error(f"[API] OpenRouter API error: {response.status} - {error_text}")
                raise Exception(f"OpenRouter API error: {response.status} - {error_text}")

            async for line in response.content:
                if line:
                    try:
                        json_line = json.loads(line.decode('utf-8').strip('data: '))
                        if 'choices' in json_line and json_line['choices']:
                            content = json_line['choices'][0]['delta'].get('content')
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        logging.error(f"[API] Failed to decode JSON: {line}")
                        continue

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
            tags={"source": "openrouter"}
        )

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
                # Non-streaming request
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                async with self.session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"[API] OpenRouter API error: {response.status} - {error_text}")
                        raise Exception(f"OpenRouter API error: {response.status} - {error_text}")

                    result = await response.json()
                    return {
                        'choices': [{
                            'message': {
                                'content': result['choices'][0]['message']['content']
                            }
                        }]
                    }

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

    async def _stream_openpipe_request(self, messages, model, temperature, max_tokens, n, top_p, presence_penalty, frequency_penalty, logprobs, top_logprobs, stop, response_format, stream_options):
        """Asynchronous OpenPipe API streaming call"""
        if not self.openpipe_base_url or not self.openpipe_path:
            raise Exception("OpenPipe URL is not properly initialized")

        logging.debug(f"[API] Making OpenPipe streaming request to model: {model}")
        
        url = urljoin(self.openpipe_base_url, self.openpipe_path)
        headers = {
            "Authorization": f"Bearer {OPENPIPE_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "n": n,
            "top_p": top_p,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
            "logprobs": logprobs,
            "top_logprobs": top_logprobs,
            "stop": stop,
            "response_format": response_format,
            "stream": True
        }
        if stream_options:
            data["stream_options"] = stream_options

        requested_at = int(time.time() * 1000)
        async with self.session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                error_text = await response.text()
                logging.error(f"[API] OpenPipe API error: {response.status} - {error_text}")
                raise Exception(f"OpenPipe API error: {response.status} - {error_text}")

            async for line in response.content:
                if line:
                    try:
                        json_line = json.loads(line.decode('utf-8').strip('data: '))
                        if 'choices' in json_line and json_line['choices']:
                            content = json_line['choices'][0]['delta'].get('content')
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        logging.error(f"[API] Failed to decode JSON: {line}")
                        continue

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
                "max_tokens": max_tokens,
                "n": n,
                "top_p": top_p,
                "presence_penalty": presence_penalty,
                "frequency_penalty": frequency_penalty,
                "logprobs": logprobs,
                "top_logprobs": top_logprobs,
                "stop": stop,
                "response_format": response_format,
                "stream_options": stream_options
            },
            resp_payload=completion_obj,
            status_code=200,
            tags={"source": "openpipe"}
        )

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=5,
        max_time=60
    )
    async def call_openpipe(self, messages: List[Dict[str, Union[str, List[Dict[str, Any]]]]], model: str, temperature: float = 0.7, stream: bool = False, n: int = 1, max_tokens: int = None, max_completion_tokens: int = None, top_p: float = None, presence_penalty: float = None, frequency_penalty: float = None, logprobs: bool = None, top_logprobs: int = None, stop: Union[str, List[str]] = None, response_format: Dict[str, str] = None, stream_options: Dict[str, bool] = None) -> Union[Dict, AsyncGenerator[str, None]]:
        if not self.openpipe_base_url or not self.openpipe_path:
            raise Exception("OpenPipe URL is not properly initialized")

        try:
            logging.debug(f"[API] Making OpenPipe request to model: {model}")
            logging.debug(f"[API] Request messages structure:")
            for msg in messages:
                logging.debug(f"[API] Message role: {msg.get('role')}")
                logging.debug(f"[API] Message content: {msg.get('content')}")

            # Check if any message contains vision content
            has_vision_content = any(
                isinstance(msg.get('content'), list) and 
                any(content.get('type') == 'image_url' for content in msg['content'])
                for msg in messages
            )
            logging.debug(f"[API] Message contains vision content: {has_vision_content}")

            # Configure parameters based on content type
            if max_tokens is None:
                max_tokens = 2000 if has_vision_content else 1000
            
            # Use provided temperature or default based on content type
            if temperature is None:
                temperature = 0.5 if has_vision_content else 0.7
            logging.debug(f"[API] Using max_tokens={max_tokens}, temperature={temperature}")

            if stream:
                return self._stream_openpipe_request(messages, model, temperature, max_tokens, n, top_p, presence_penalty, frequency_penalty, logprobs, top_logprobs, stop, response_format, stream_options)
            else:
                # Non-streaming request
                url = urljoin(self.openpipe_base_url, self.openpipe_path)
                headers = {
                    "Authorization": f"Bearer {OPENPIPE_API_KEY}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "n": n,
                    "top_p": top_p,
                    "presence_penalty": presence_penalty,
                    "frequency_penalty": frequency_penalty,
                    "logprobs": logprobs,
                    "top_logprobs": top_logprobs,
                    "stop": stop,
                    "response_format": response_format
                }

                async with self.session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"[API] OpenPipe API error: {response.status} - {error_text}")
                        raise Exception(f"OpenPipe API error: {response.status} - {error_text}")

                    result = await response.json()
                    return {
                        'choices': [{
                            'message': {
                                'content': result['choices'][0]['message']['content']
                            }
                        }]
                    }

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
            elif isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)):
                logging.error(f"[API] Connection error: {str(e)}")
                raise Exception("🌐 Connection error. Please check your internet connection and try again.")
            else:
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
