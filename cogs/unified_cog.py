"""
Unified cog that consolidates all model functionality with two-step routing and rate limit handling.
"""
import discord
from discord.ext import commands
import logging
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Dict, List, AsyncGenerator, Union
import re
from urllib.parse import urlparse
from config.webhook_config import load_webhooks, MAX_RETRIES, WEBHOOK_TIMEOUT
import backoff

class RateLimitTracker:
    def __init__(self):
        self.rate_limits = {}  # {model: {'reset_at': timestamp, 'remaining': count}}
        self.backoff_times = {}  # {model: seconds_to_wait}
        self.MIN_BACKOFF = 1
        self.MAX_BACKOFF = 60

    def is_rate_limited(self, model: str) -> bool:
        """Check if a model is currently rate limited"""
        if model not in self.rate_limits:
            return False
        limit_info = self.rate_limits[model]
        return limit_info['remaining'] <= 0 and datetime.now().timestamp() < limit_info['reset_at']

    def update_rate_limit(self, model: str, remaining: int, reset_at: float):
        """Update rate limit info for a model"""
        self.rate_limits[model] = {
            'remaining': remaining,
            'reset_at': reset_at
        }

    def get_backoff_time(self, model: str) -> float:
        """Get current backoff time for a model"""
        return self.backoff_times.get(model, self.MIN_BACKOFF)

    def increase_backoff(self, model: str):
        """Increase backoff time for a model"""
        current = self.backoff_times.get(model, self.MIN_BACKOFF)
        self.backoff_times[model] = min(current * 2, self.MAX_BACKOFF)

    def reset_backoff(self, model: str):
        """Reset backoff time for a model"""
        self.backoff_times[model] = self.MIN_BACKOFF

class UnifiedCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.name = "UnifiedRouter"
        self.active_channels = set()
        self.webhooks = load_webhooks()
        self.session = aiohttp.ClientSession()
        self.context_cog = bot.get_cog('ContextCog')
        self.handled_messages = set()
        self._image_processing_lock = asyncio.Lock()
        self.last_model_used = {}  # Track last model per channel for loop prevention
        self.rate_limiter = RateLimitTracker()
        
        # Get API client from bot instance
        self.api_client = getattr(bot, 'api_client', None)
        if not self.api_client:
            logging.error("[UnifiedRouter] No API client found on bot")
            raise ValueError("Bot must have api_client attribute")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[UnifiedRouter] Failed to load temperatures.json: {e}")
            self.temperatures = {}

        # Load system prompts
        try:
            with open('prompts/consolidated_prompts.json', 'r', encoding='utf-8') as f:
                self.prompts = json.load(f).get('system_prompts', {})
        except Exception as e:
            logging.error(f"[UnifiedRouter] Failed to load prompts: {e}")
            self.prompts = {}

        # Comprehensive model configuration
        self.model_config = {
            'ministral': {
                'name': 'Ministral',
                'model': 'mistralai/ministral-3b',
                'temperature': self.temperatures.get('Mixtral', 0.7),
                'keywords': ['general', 'chat', 'conversation'],
                'prompt_key': 'ministral',
                'supports_vision': False,
                'trigger_words': ['ministral']
            },
            'gemini': {
                'name': 'Gemini',
                'model': 'google/gemini-pro-1.5-exp',
                'fallback_model': 'google/gemini-pro-1.5',
                'temperature': self.temperatures.get('Gemini-Pro', 0.7),
                'keywords': ['image', 'analyze', 'describe', 'visual'],
                'prompt_key': 'gemini',
                'supports_vision': True,
                'trigger_words': ['gemini']
            },
            'sonnet': {
                'name': 'Sonnet',
                'model': 'anthropic/claude-3-5-sonnet:beta',
                'temperature': self.temperatures.get('Claude-3.5-Sonnet', 0.85),
                'keywords': ['code', 'technical', 'programming', 'development'],
                'prompt_key': 'sonnet',
                'supports_vision': False,
                'trigger_words': ['sonnet']
            },
            'goliath': {
                'name': 'Goliath',
                'model': 'alpindale/goliath-120b',
                'temperature': self.temperatures.get('Goliath', 0.8),
                'keywords': ['complex', 'detailed', 'analysis', 'research'],
                'prompt_key': 'goliath',
                'supports_vision': False,
                'trigger_words': ['120b', 'goliath']
            },
            'sonar': {
                'name': 'Sonar',
                'model': 'perplexity/llama-3.1-sonar-small-128k-online',
                'fallback_model': 'perplexity/llama-3.1-sonar-large-128k-online',
                'temperature': self.temperatures.get('Sonar', 0.7),
                'keywords': ['news', 'current', 'events', 'updates'],
                'prompt_key': 'sonar',
                'supports_vision': False,
                'trigger_words': ['sonar']
            },
            'hermes': {
                'name': 'Hermes',
                'model': 'nousresearch/hermes-3-llama-3.1-405b:free',
                'fallback_model': 'nousresearch/hermes-3-llama-3.1-405b',
                'temperature': self.temperatures.get('Hermes', 0.7),
                'keywords': ['help', 'support', 'guidance', 'advice'],
                'prompt_key': 'hermes',
                'supports_vision': False,
                'trigger_words': ['hermes']
            },
            'sorcerer': {
                'name': 'Sorcerer',
                'model': 'raifle/sorcererlm-8x22b',
                'temperature': self.temperatures.get('Sorcerer', 0.7),
                'keywords': ['creative', 'story', 'roleplay', 'fantasy'],
                'prompt_key': 'sorcerer',
                'supports_vision': False,
                'trigger_words': ['sorcerer', 'sorcererlm']
            },
            'sydney': {
                'name': 'Sydney',
                'model': 'meta-llama/llama-3.1-405b-instruct:free',
                'fallback_model': 'meta-llama/llama-3.1-405b-instruct',
                'temperature': self.temperatures.get('Sydney', 0.7),
                'keywords': ['chat', 'friendly', 'casual', 'social'],
                'prompt_key': 'sydney',
                'supports_vision': False,
                'trigger_words': ['syd', 'sydney']
            },
            'dolphin': {
                'name': 'Dolphin',
                'model': 'cognitivecomputations/dolphin-mixtral-8x22b',
                'temperature': self.temperatures.get('Dolphin', 0.7),
                'keywords': ['uncensored', 'mature', 'controversial'],
                'prompt_key': 'dolphin',
                'supports_vision': False,
                'trigger_words': ['dolphin']
            }
        }

        # Build bypass keywords from all trigger words
        all_trigger_words = []
        for config in self.model_config.values():
            all_trigger_words.extend(config['trigger_words'])
        
        self.bypass_keywords = [
            r'\b(use|switch to|try|with)\s+(' + '|'.join(all_trigger_words) + r')\b',
            r'\b(' + '|'.join(all_trigger_words) + r')\s+(please|now|instead)\b',
            r'^(' + '|'.join(all_trigger_words) + r')[,:]\s',
            r'\b(' + '|'.join(all_trigger_words) + r')\b'
        ]

        # Context window settings
        self.default_context_window = 50
        self.max_context_window = 500
        self.context_windows = {}  # Track custom context windows per channel

    async def handle_rate_limit(self, model: str, retry_after: float):
        """Handle rate limit response"""
        self.rate_limiter.update_rate_limit(
            model=model,
            remaining=0,
            reset_at=datetime.now().timestamp() + retry_after
        )
        self.rate_limiter.increase_backoff(model)
        await asyncio.sleep(retry_after)

    async def make_api_request(self, messages: List[Dict], model_config: Dict, stream: bool = True) -> AsyncGenerator[str, None]:
        """Make API request with rate limit handling"""
        model = model_config['model']
        fallback_model = model_config.get('fallback_model')

        while True:
            if self.rate_limiter.is_rate_limited(model):
                if fallback_model:
                    logging.warning(f"[UnifiedRouter] Model {model} is rate limited, trying fallback {fallback_model}")
                    model = fallback_model
                    if self.rate_limiter.is_rate_limited(model):
                        await asyncio.sleep(self.rate_limiter.get_backoff_time(model))
                        continue
                else:
                    await asyncio.sleep(self.rate_limiter.get_backoff_time(model))
                    continue

            try:
                async for chunk in self.api_client.call_openrouter(
                    messages=messages,
                    model=model,
                    temperature=model_config['temperature'],
                    stream=stream
                ):
                    if chunk and 'content' in chunk:
                        yield chunk['content']
                        
                # Success, reset backoff
                self.rate_limiter.reset_backoff(model)
                break

            except Exception as e:
                if hasattr(e, 'status') and e.status == 429:
                    retry_after = float(getattr(e, 'retry_after', 5))
                    await self.handle_rate_limit(model, retry_after)
                    continue
                else:
                    logging.error(f"[UnifiedRouter] API error: {str(e)}")
                    if fallback_model and model != fallback_model:
                        logging.warning(f"[UnifiedRouter] Trying fallback model {fallback_model}")
                        model = fallback_model
                        continue
                    raise

    async def determine_route(self, message: discord.Message) -> Dict:
        """Two-step routing process"""
        try:
            # Check for direct model mentions first
            content = message.content.lower()
            for model_id, config in self.model_config.items():
                if any(word in content for word in config['trigger_words']):
                    return config

            # Check for images - route to vision-capable model
            if self.get_image_urls(message):
                return self.model_config['gemini']

            # Format the routing prompt exactly as in router_cog.py
            routing_prompt = f"""Analyze this message and route it to the most appropriate model based on content. Return ONLY the model name, no explanation.

Message: "{message.content}"

Available Models:
1. Sonar - Current events, news, updates, time-sensitive info
2. Dolphin - Uncensored topics, mature content, controversial subjects
3. Hermes - Mental health, crisis support, emotional guidance
4. Sorcerer - Fantasy roleplay, character immersion, standard RP
5. Goliath - Long-form stories, detailed plots, epic narratives
6. Sydney - Emotional support, friendship, daily life chat
7. Sonnet - Technical tasks, coding, software engineering
8. Ministral - Default for general conversation

Model name:"""

            # Make routing request to Ministral with NO context
            messages = [
                {"role": "system", "content": "You are a message routing assistant. Return only the model name."},
                {"role": "user", "content": routing_prompt}
            ]

            # Get routing response
            response = ""
            async for chunk in self.make_api_request(
                messages=messages,
                model_config=self.model_config['ministral'],
                stream=False
            ):
                response += chunk

            # Clean up response and get model config
            model_name = response.strip().lower()
            for config in self.model_config.values():
                if config['name'].lower() == model_name:
                    if not self.check_routing_loop(message.channel.id, config['name']):
                        return config

            return self.model_config['ministral']

        except Exception as e:
            logging.error(f"[UnifiedRouter] Error determining route: {e}")
            return self.model_config['ministral']

    async def format_messages_for_context(self, message: discord.Message, model_config: Dict) -> List[Dict]:
        """Format messages including context window for API request"""
        messages = []
        
        # Add system prompt
        system_prompt = self.format_system_prompt(message, model_config)
        messages.append({"role": "system", "content": system_prompt})
        
        # Get context window size for this channel
        context_size = self.context_windows.get(str(message.channel.id), self.default_context_window)
        context_size = min(context_size, self.max_context_window)
        
        # Get context messages
        if self.context_cog:
            try:
                context = await self.context_cog.get_context_messages(
                    str(message.channel.id),
                    limit=context_size,
                    exclude_message_id=str(message.id)
                )
                for ctx_msg in context:
                    role = "assistant" if ctx_msg['is_assistant'] else "user"
                    messages.append({"role": role, "content": ctx_msg['content']})
            except Exception as e:
                logging.error(f"[UnifiedRouter] Failed to get context: {e}")

        # Handle current message content
        content = []
        
        # Add text content if present
        if message.content:
            content.append({
                "type": "text",
                "text": message.content
            })
            
        # Add images if present and model supports vision
        if model_config.get('supports_vision', False):
            image_urls = self.get_image_urls(message)
            for url in image_urls:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            
        # Add the user message
        if len(content) == 1 and content[0]["type"] == "text":
            messages.append({"role": "user", "content": content[0]["text"]})
        else:
            messages.append({"role": "user", "content": content})
            
        return messages

    async def generate_response(self, message: discord.Message, model_config: Dict) -> AsyncGenerator[str, None]:
        """Generate response using OpenRouter API"""
        try:
            # Start typing indicator
            await self.start_typing(message.channel)
            
            # Format messages with context
            messages = await self.format_messages_for_context(message, model_config)
            
            # Try primary model first
            try:
                async for chunk in self.api_client.call_openrouter(
                    messages=messages,
                    model=model_config['model'],
                    temperature=model_config['temperature'],
                    stream=True,
                    user_id=str(message.author.id),
                    guild_id=str(message.guild.id) if message.guild else None
                ):
                    if chunk and 'content' in chunk:
                        yield chunk['content']
                return
            except Exception as e:
                logging.warning(f"[UnifiedRouter] Primary model failed: {e}")

            # Try fallback model if available
            fallback_model = model_config.get('fallback_model')
            if fallback_model:
                try:
                    logging.info(f"[UnifiedRouter] Trying fallback model: {fallback_model}")
                    async for chunk in self.api_client.call_openrouter(
                        messages=messages,
                        model=fallback_model,
                        temperature=model_config['temperature'],
                        stream=True,
                        user_id=str(message.author.id),
                        guild_id=str(message.guild.id) if message.guild else None
                    ):
                        if chunk and 'content' in chunk:
                            yield chunk['content']
                    return
                except Exception as e:
                    logging.error(f"[UnifiedRouter] Fallback model failed: {e}")

            yield f"❌ Error: Failed to generate response with {model_config['name']}"

        except Exception as e:
            logging.error(f"[UnifiedRouter] Error generating response: {e}")
            yield f"❌ Error: {str(e)}"

    async def send_to_webhook(self, webhook_url: str, content: str, username: str, retries: int = 0) -> bool:
        """Send response through webhook with specific username"""
        if retries >= MAX_RETRIES:
            logging.error(f"[UnifiedRouter] Max retries reached for webhook")
            return False

        try:
            async with self.session.post(
                webhook_url,
                json={"content": content, "username": username},
                timeout=WEBHOOK_TIMEOUT
            ) as response:
                if response.status == 429:  # Rate limited
                    retry_after = float(response.headers.get('Retry-After', 5))
                    await asyncio.sleep(retry_after)
                    return await self.send_to_webhook(webhook_url, content, username, retries + 1)
                
                return 200 <= response.status < 300

        except asyncio.TimeoutError:
            logging.warning(f"[UnifiedRouter] Webhook request timed out, retrying...")
            return await self.send_to_webhook(webhook_url, content, username, retries + 1)
        except Exception as e:
            logging.error(f"[UnifiedRouter] Error sending to webhook: {e}")
            return False

    async def handle_message(self, message: discord.Message):
        """Process message and send response"""
        try:
            # Determine appropriate model
            model_config = await self.determine_route(message)
            
            # Generate response
            response = ""
            async for chunk in self.generate_response(message, model_config):
                if chunk:
                    response += chunk
                    
            # Send through webhook if available
            if self.webhooks:
                success = False
                for webhook_url in self.webhooks:
                    if await self.send_to_webhook(webhook_url, response, model_config['name']):
                        success = True
                        break
                        
                if not success:
                    # Fallback to regular message
                    await message.channel.send(f"[{model_config['name']}] {response}")
            else:
                # No webhooks configured
                await message.channel.send(f"[{model_config['name']}] {response}")
                
            # Add to context
            if self.context_cog:
                try:
                    await self.context_cog.add_message_to_context(
                        message.id,
                        str(message.channel.id),
                        str(message.guild.id) if message.guild else None,
                        str(message.author.id),
                        response,
                        True,
                        model_config['name'],
                        None
                    )
                except Exception as e:
                    logging.error(f"[UnifiedRouter] Failed to add to context: {e}")

        except Exception as e:
            logging.error(f"[UnifiedRouter] Error handling message: {e}")
            await message.channel.send(f"❌ Error: {str(e)}")

    def should_handle_message(self, message: discord.Message) -> bool:
        """Determine if message should be handled"""
        if message.author.bot:
            return False
            
        if message.id in self.handled_messages:
            return False
            
        if isinstance(message.channel, discord.DMChannel):
            return True
            
        if self.bot.user in message.mentions:
            return True
            
        if message.channel.id in self.active_channels:
            return True
            
        return False

    @commands.command(name='set_context_window')
    @commands.has_permissions(manage_channels=True)
    async def set_context_window(self, ctx, size: int):
        """Set custom context window size for the channel"""
        if not (50 <= size <= 500):
            await ctx.send("Context window size must be between 50 and 500 messages.")
            return
            
        self.context_windows[str(ctx.channel.id)] = size
        await ctx.send(f"Context window size set to {size} messages for this channel.")

    @commands.command(name='activate')
    @commands.has_permissions(manage_channels=True)
    async def activate(self, ctx):
        """Activate UnifiedRouter in current channel"""
        self.active_channels.add(ctx.channel.id)
        await ctx.send("UnifiedRouter activated in this channel.")

    @commands.command(name='deactivate')
    @commands.has_permissions(manage_channels=True)
    async def deactivate(self, ctx):
        """Deactivate UnifiedRouter in current channel"""
        self.active_channels.discard(ctx.channel.id)
        # Clear any loop detection state
        self.last_model_used.pop(ctx.channel.id, None)
        self.last_model_used.pop(f"{ctx.channel.id}_count", None)
        await ctx.send("UnifiedRouter deactivated in this channel.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if not self.should_handle_message(message):
            return
            
        try:
            self.handled_messages.add(message.id)
            await self.handle_message(message)
        except Exception as e:
            logging.error(f"[UnifiedRouter] Error in on_message: {e}")

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        asyncio.create_task(self.session.close())

async def setup(bot):
    """Add UnifiedRouter cog to bot"""
    await bot.add_cog(UnifiedCog(bot))
