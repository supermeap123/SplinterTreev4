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

    @commands.command(name='hook')
    async def hook_command(self, ctx, *, content: str = None):
        """Send a message through configured webhooks"""
        if not content:
            await ctx.reply("❌ Please provide a message after !hook")
            return

        if DEBUG_LOGGING:
            logging.info(f"[WebhookCog] Processing hook command: {content}")

        # Find an appropriate LLM cog to handle the message
        response = None
        used_cog = None
        
        # Try router cog first if available
        router_cog = self.bot.get_cog('RouterCog')
        if router_cog and hasattr(router_cog, 'route_message'):
            try:
                # Create a copy of the message with modified content
                modified_message = discord.Message.__new__(discord.Message)
                modified_message.__dict__.update(ctx.message.__dict__)
                modified_message.content = content

                cog = await router_cog.route_message(modified_message)
                if cog and hasattr(cog, 'generate_response'):
                    response_stream = await cog.generate_response(modified_message)
                    if response_stream:
                        response = ""
                        async for chunk in response_stream:
                            if chunk:
                                response += chunk
                        used_cog = cog
            except Exception as e:
                logging.error(f"[WebhookCog] Error using router: {str(e)}")

        # If router didn't work, try direct cog matching
        if not response:
            for cog in self.bot.cogs.values():
                if hasattr(cog, 'trigger_words') and hasattr(cog, 'generate_response'):
                    msg_content = content.lower()
                    if any(word in msg_content for word in cog.trigger_words):
                        try:
                            # Create a copy of the message with modified content
                            modified_message = discord.Message.__new__(discord.Message)
                            modified_message.__dict__.update(ctx.message.__dict__)
                            modified_message.content = content

                            response_stream = await cog.generate_response(modified_message)
                            if response_stream:
                                response = ""
                                async for chunk in response_stream:
                                    if chunk:
                                        response += chunk
                                used_cog = cog
                                break
                        except Exception as e:
                            logging.error(f"[WebhookCog] Error with cog {cog.__class__.__name__}: {str(e)}")

        if response:
            # Format response with model name if available
            formatted_response = f"[{used_cog.name}] {response}" if hasattr(used_cog, 'name') else response

            # Send to webhooks
            success = await self.broadcast_to_webhooks(formatted_response)
            
            if success:
                await ctx.message.add_reaction('✅')
            else:
                await ctx.message.add_reaction('❌')
                await ctx.reply("❌ Failed to send message to webhooks")
        else:
            await ctx.reply("❌ No LLM cog responded to the message")

async def setup(bot):
    """Add the webhook cog to the bot"""
    await bot.add_cog(WebhookCog(bot))
