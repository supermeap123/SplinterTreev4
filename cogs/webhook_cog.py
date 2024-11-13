"""
Webhook integration cog for sending LLM responses through Discord webhooks.
"""
import discord
from discord.ext import commands
import aiohttp
import logging
import asyncio
from config.webhook_config import load_webhooks, MAX_RETRIES, WEBHOOK_TIMEOUT, DEBUG_LOGGING

class WebhookCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.webhooks = load_webhooks()
        self.session = aiohttp.ClientSession()
        if DEBUG_LOGGING:
            logging.info(f"[WebhookCog] Initialized with {len(self.webhooks)} webhooks")

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        asyncio.create_task(self.session.close())

    async def send_to_webhook(self, webhook_url: str, content: str, retries: int = 0) -> bool:
        """
        Send content to a Discord webhook
        Returns True if successful, False otherwise
        """
        if retries >= MAX_RETRIES:
            logging.error(f"[WebhookCog] Max retries reached for webhook")
            return False

        try:
            async with self.session.post(
                webhook_url,
                json={"content": content},
                timeout=WEBHOOK_TIMEOUT
            ) as response:
                if response.status == 429:  # Rate limited
                    retry_after = float(response.headers.get('Retry-After', 5))
                    await asyncio.sleep(retry_after)
                    return await self.send_to_webhook(webhook_url, content, retries + 1)
                
                return 200 <= response.status < 300

        except asyncio.TimeoutError:
            logging.warning(f"[WebhookCog] Webhook request timed out, retrying...")
            return await self.send_to_webhook(webhook_url, content, retries + 1)
        except Exception as e:
            logging.error(f"[WebhookCog] Error sending to webhook: {str(e)}")
            return False

    async def broadcast_to_webhooks(self, content: str) -> bool:
        """
        Broadcast content to all configured webhooks
        Returns True if at least one webhook succeeded
        """
        if not self.webhooks:
            if DEBUG_LOGGING:
                logging.warning("[WebhookCog] No webhooks configured")
            return False

        success = False
        for webhook_url in self.webhooks:
            result = await self.send_to_webhook(webhook_url, content)
            success = success or result

        return success

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages with !hook prefix"""
        if message.author.bot:
            return

        # Check if message starts with !hook
        if not message.content.startswith('!hook '):
            return

        # Remove !hook prefix
        content = message.content[6:].strip()
        if not content:
            await message.channel.send("❌ Please provide a message after !hook")
            return

        # Process the message through the appropriate LLM cog
        response = None
        for cog in self.bot.cogs.values():
            if hasattr(cog, 'trigger_words'):
                msg_content = content.lower()
                if any(word in msg_content for word in cog.trigger_words):
                    # Create a copy of the message with modified content
                    modified_message = discord.Message.__new__(discord.Message)
                    modified_message.__dict__.update(message.__dict__)
                    modified_message.content = content

                    # Generate response using the cog
                    response_stream = await cog.generate_response(modified_message)
                    if response_stream:
                        response = ""
                        async for chunk in response_stream:
                            if chunk:
                                response += chunk
                        break

        if response:
            # Format response with model name
            formatted_response = f"[{cog.name}] {response}"

            # Send to webhooks
            success = await self.broadcast_to_webhooks(formatted_response)
            
            if success:
                await message.add_reaction('✅')
            else:
                await message.add_reaction('❌')
                await message.channel.send("❌ Failed to send message to webhooks")
        else:
            await message.channel.send("❌ No LLM cog responded to the message")

async def setup(bot):
    """Add the webhook cog to the bot"""
    await bot.add_cog(WebhookCog(bot))
