import discord
from discord.ext import commands
import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import time
from shared.utils import analyze_emotion, log_interaction
from shared.api import api
import re
import aiohttp
import asyncio
import tempfile
from cogs.context_cog import ContextCog  # Import ContextCog

class RerollView(discord.ui.View):
    def __init__(self, cog, message, original_response):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.message = message
        self.original_response = original_response

    @discord.ui.button(label="🎲 Reroll Response", style=discord.ButtonStyle.secondary, custom_id="reroll_button")
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            # Process message again for new response
            new_response = await self.cog.generate_response(self.message)
            if new_response:
                # Format response with model name
                prefixed_response = f"[{self.cog.name}] {new_response}"
                # Edit the original response
                await interaction.message.edit(content=prefixed_response, view=self)
                # Add emotion reaction
                emotion = analyze_emotion(new_response)
                if emotion:
                    try:
                        await self.message.add_reaction(emotion)
                    except discord.errors.Forbidden:
                        logging.warning(f"[{self.cog.name}] Missing permission to add reaction")
            else:
                await interaction.followup.send("Failed to generate a new response. Please try again.", ephemeral=True)
        except Exception as e:
            logging.error(f"Error in reroll button: {str(e)}")
            await interaction.followup.send("An error occurred while generating a new response.", ephemeral=True)

class BaseCog(commands.Cog):
    def __init__(self, bot, name, nickname, trigger_words, model, provider="openrouter", prompt_file=None, supports_vision=False):
        self.bot = bot
        self.name = name
        self.nickname = nickname
        self.trigger_words = [word.lower() for word in trigger_words]  # Convert trigger words to lowercase
        self.model = model
        self.provider = provider
        self.supports_vision = supports_vision
        self.context_cog = self.bot.get_cog('ContextCog')  # Get ContextCog instance
        self.context_messages = {}  # Store context message counts per channel

        # Load prompt
        try:
            with open('prompts/consolidated_prompts.json', 'r', encoding='utf-8') as f:
                consolidated_prompts = json.load(f).get('system_prompts', {})
                if prompt_file:
                    raw_prompt = consolidated_prompts.get(prompt_file.lower(), f"You are {name}, an advanced AI assistant focused on providing accurate and helpful responses.")
                else:
                    raw_prompt = consolidated_prompts.get(name.lower(), f"You are {name}, an advanced AI assistant focused on providing accurate and helpful responses.")
            logging.debug(f"[{name}] Loaded raw prompt: {raw_prompt}")
        except Exception as e:
            logging.warning(f"Failed to load prompt for {self.name}, using default: {str(e)}")
            raw_prompt = f"You are {name}, an advanced AI assistant focused on providing accurate and helpful responses."

        # Assign the raw prompt; substitution will occur in process_message
        self.raw_prompt = raw_prompt
        self.formatted_prompt = raw_prompt

    def check_triggers(self, content: str) -> bool:
        """Check if the message content contains any trigger words"""
        content = content.lower()
        # Check if any trigger word appears as a substring in the content
        return any(trigger in content for trigger in self.trigger_words)

    def is_reply_to_bot(self, message):
        """Check if the message is a reply to this bot's persona and return the referenced message content"""
        if message.reference and message.reference.resolved:
            referenced_message = message.reference.resolved
            if referenced_message.author == self.bot.user:
                # Check if the referenced message starts with this persona's name
                if referenced_message.content.startswith(f"[{self.name}]"):
                    return referenced_message.content
        return None

    async def handle_message(self, message):
        """Handle incoming messages - this is called by the bot's on_message event"""
        if message.author == self.bot.user:
            return

        # Check if message triggers this cog
        is_triggered = self.check_triggers(message.content)
        replied_content = self.is_reply_to_bot(message)

        if is_triggered or replied_content:
            logging.debug(f"[{self.name}] Triggered by message: {message.content}")
            try:
                # Check permissions
                permissions = message.channel.permissions_for(message.guild.me if message.guild else self.bot.user)
                can_send = permissions.send_messages if hasattr(permissions, 'send_messages') else True
                can_add_reactions = permissions.add_reactions if hasattr(permissions, 'add_reactions') else True

                if not can_send:
                    logging.warning(f"[{self.name}] Missing permission to send messages in channel {message.channel.id}")
                    return

                # Process images first if needed
                if not self.supports_vision and message.attachments:
                    await self.process_images(message)

                # Generate response
                response = await self.generate_response(message, replied_content)

                if response:
                    # Send the response
                    sent_message = await self.handle_response(response, message)
                    if sent_message:
                        # Log interaction
                        try:
                            log_interaction(
                                user_id=message.author.id,
                                guild_id=message.guild.id if message.guild else None,
                                persona_name=self.name,
                                user_message=message.content,
                                assistant_reply=response,
                                emotion=analyze_emotion(response),
                                channel_id=str(message.channel.id)
                            )
                            logging.debug(f"[{self.name}] Logged interaction for user {message.author.id}")
                        except Exception as e:
                            logging.error(f"[{self.name}] Failed to log interaction: {str(e)}", exc_info=True)
                        return response, None
                    else:
                        logging.error(f"[{self.name}] No response received from API")
                        if can_add_reactions:
                            await message.add_reaction('❌')
                        if can_send:
                            await message.reply(f"[{self.name}] Failed to generate a response. Please try again.")
                        return None, None

            except Exception as e:
                logging.error(f"[{self.name}] Error in message handling: {str(e)}", exc_info=True)
                try:
                    if can_add_reactions:
                        await message.add_reaction('❌')
                    if can_send:
                        error_msg = str(e)
                        if "insufficient_quota" in error_msg.lower():
                            await message.reply("⚠️ API quota exceeded. Please try again later.")
                        elif "invalid_api_key" in error_msg.lower():
                            await message.reply("🔑 API configuration error. Please contact the bot administrator.")
                        elif "rate_limit_exceeded" in error_msg.lower():
                            await message.reply("⏳ Rate limit exceeded. Please try again later.")
                        else:
                            await message.reply(f"[{self.name}] An error occurred while processing your request.")
                except discord.errors.Forbidden:
                    logging.error(f"[{self.name}] Missing permissions to send error message or add reaction")
                return None, None

    async def process_images(self, message):
        """Process images and store descriptions in the database"""
        if not message.attachments:
            return

        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                try:
                    # Use Llama with vision capabilities
                    messages_for_vision = [
                        {"role": "system", "content": "You are a helpful assistant that provides detailed descriptions of images."},
                        {"role": "user", "content": [
                            {"type": "text", "text": "Please provide a detailed description of this image."},
                            {"type": "image_url", "image_url": {"url": attachment.url}}
                        ]}
                    ]
                    vision_response = await api.call_openrouter(messages_for_vision, "meta-llama/llama-3.2-11b-instruct:free")
                    if vision_response and 'choices' in vision_response and len(vision_response['choices']) > 0:
                        description = vision_response['choices'][0]['message']['content']
                        # Log the image description interaction
                        try:
                            log_interaction(
                                user_id=message.author.id,
                                guild_id=message.guild.id if message.guild else None,
                                persona_name="Llama-Vision",
                                user_message=f"Image URL: {attachment.url}",
                                assistant_reply=description,
                                channel_id=str(message.channel.id)
                            )
                            logging.debug(f"[Llama-Vision] Logged image description for user {message.author.id}")
                        except Exception as e:
                            logging.error(f"[Llama-Vision] Failed to log image description: {str(e)}")
                except Exception as e:
                    logging.error(f"[{self.name}] Failed to process image: {str(e)}")

    def filter_consecutive_duplicates(self, messages):
        """Filter out consecutive duplicate messages"""
        filtered = []
        for message in messages:
            if not filtered or message != filtered[-1]:
                filtered.append(message)
        return filtered

    def remove_duplicate_username(self, content):
        """Remove duplicate usernames from the content"""
        pattern = r'\[(\w+)\]\s*\[(\w+)\]'
        return re.sub(pattern, r'[\1]', content)

    async def get_context_messages(self, channel_id: str) -> list:
        """Get the last N context messages for a channel"""
        n = self.context_messages.get(channel_id, 5)  # Default to 5 if not set
        messages = await self.context_cog.get_context_messages(channel_id, limit=n)
        return messages

    @commands.command(name='set_context')
    @commands.has_permissions(manage_messages=True)
    async def set_context_messages(self, ctx, count: int):
        """Set the number of context messages for the current channel"""
        if count < 1 or count > 20:
            await ctx.send("Context message count must be between 1 and 20.")
            return
        self.context_messages[str(ctx.channel.id)] = count
        await ctx.send(f"Context message count for this channel set to {count}.")

    async def generate_response(self, message, replied_content=None):
        """Generate a response without handling it"""
        try:
            # Get local timezone
            local_tz = datetime.now().astimezone().tzinfo
            current_time = datetime.now(local_tz)

            # Format system prompt with dynamic variables
            formatted_prompt = self.raw_prompt.format(
                discord_user=message.author.display_name,
                discord_user_id=message.author.id,
                local_time=current_time.strftime("%I:%M %p"),
                local_timezone=str(local_tz),
                server_name=message.guild.name if message.guild else "Direct Message",
                channel_name=message.channel.name if hasattr(message.channel, 'name') else "DM"
            )

            # Get dynamic prompt if one exists
            dynamic_prompt = self.get_dynamic_prompt(message)
            if dynamic_prompt:
                # Add dynamic prompt as a second system message
                messages = [
                    {"role": "system", "content": formatted_prompt},
                    {"role": "system", "content": dynamic_prompt}
                ]
            else:
                messages = [
                    {"role": "system", "content": formatted_prompt}
                ]

            # Get context messages
            channel_id = str(message.channel.id)
            history_messages = await self.get_context_messages(channel_id)
            
            # Process messages to create conversation context
            for msg in history_messages:
                role = "assistant" if msg['is_assistant'] else "user"
                content = msg['content']
                if msg['is_assistant']:
                    content = self.remove_duplicate_username(f"[{msg['persona_name']}] {content}")
                messages.append({"role": role, "content": content})

            # Add replied-to message if it exists
            if replied_content:
                messages.append({"role": "assistant", "content": replied_content})

            # Add current message
            messages.append({
                "role": "user",
                "content": message.content
            })

            # Filter out consecutive duplicate messages
            messages = self.filter_consecutive_duplicates(messages)

            logging.debug(f"[{self.name}] Sending {len(messages)} messages to API")
            logging.debug(f"[{self.name}] Formatted prompt: {formatted_prompt}")
            if dynamic_prompt:
                logging.debug(f"[{self.name}] Added dynamic prompt: {dynamic_prompt}")

            # Get temperature for this agent
            temperature = self.get_temperature(self.name)
            logging.debug(f"[{self.name}] Using temperature: {temperature}")

            # Call API based on provider with temperature
            if self.provider == "openrouter":
                response_data = await api.call_openrouter(messages, self.model, temperature=temperature)
            else:  # openpipe
                response_data = await api.call_openpipe(messages, self.model, temperature=temperature)

            if response_data and 'choices' in response_data and len(response_data['choices']) > 0:
                response = response_data['choices'][0]['message']['content']
                # Remove duplicate usernames from the response
                response = self.remove_duplicate_username(response)
                logging.debug(f"[{self.name}] Got response: {response}")
                return response

            logging.warning(f"[{self.name}] No valid response received from API")
            return None

        except Exception as e:
            logging.error(f"Error processing message for {self.name}: {str(e)}")
            return None

    def sanitize_username(self, username: str) -> str:
        """Sanitize username to match the pattern ^[a-zA-Z0-9_-]+$"""
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^\w\-]', '_', username)
        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized

    def get_dynamic_prompt(self, ctx):
        """Get dynamic prompt for channel/server if one exists"""
        guild_id = str(ctx.guild.id) if ctx.guild else None
        channel_id = str(ctx.channel.id)

        prompts_file = "dynamic_prompts.json"
        if not os.path.exists(prompts_file):
            return None

        try:
            with open(prompts_file, "r") as f:
                dynamic_prompts = json.load(f)

            if guild_id in dynamic_prompts and channel_id in dynamic_prompts[guild_id]:
                return dynamic_prompts[guild_id][channel_id]
            elif channel_id in dynamic_prompts:
                return dynamic_prompts[channel_id]
            else:
                return None
        except Exception as e:
            logging.error(f"Error getting dynamic prompt: {str(e)}")
            return None

    def get_temperature(self, agent_name):
        """Get temperature for agent if one exists"""
        temperatures_file = "temperatures.json"
        if not os.path.exists(temperatures_file):
            return None  # Let API use default temperature

        try:
            with open(temperatures_file, "r") as f:
                temperatures = json.load(f)
            return temperatures.get(agent_name)  # Return None if not found
        except Exception as e:
            logging.error(f"Error getting temperature: {str(e)}")
            return None

    @commands.Cog.listener()
    async def on_ready(self):
        """Ensure set_context command is only registered once"""
        if 'set_context' not in self.bot.all_commands:
            self.bot.add_command(self.set_context_messages)
