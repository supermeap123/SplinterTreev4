import discord
from discord.ext import commands
import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import time
from shared.utils import analyze_emotion, log_interaction, get_message_history, store_alt_text, get_alt_text, get_unprocessed_images
from shared.api import api
import re
import aiohttp
import asyncio
import tempfile

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
        self.trigger_words = trigger_words
        self.model = model
        self.provider = provider
        self.supports_vision = supports_vision

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

    async def create_response_file(self, response_text: str, message_id: str) -> discord.File:
        """Create a markdown file containing the response"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as temp_file:
            temp_file.write(response_text)
            temp_file_path = temp_file.name

        # Create Discord File object
        file = discord.File(
            temp_file_path,
            filename=f'model_response_{message_id}.md'
        )
        # Schedule file deletion
        async def delete_temp_file():
            await asyncio.sleep(1)  # Wait a bit to ensure file is sent
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logging.error(f"Failed to delete temp file: {str(e)}")
        asyncio.create_task(delete_temp_file())
        return file

    async def handle_response(self, response_text, message, referenced_message=None):
        """Handle the response formatting and sending"""
        try:
            # Check permissions
            permissions = message.channel.permissions_for(message.guild.me if message.guild else self.bot.user)
            can_send = permissions.send_messages if hasattr(permissions, 'send_messages') else True
            can_dm = True  # Assume DMs are possible until proven otherwise

            if not can_send and not can_dm:
                logging.error(f"[{self.name}] No available method to send response")
                return None

            # Check if message content is spoilered using ||content|| format
            is_spoilered = message.content.startswith('||') and message.content.endswith('||')

            # Format response with model name
            prefixed_response = f"[{self.name}] {response_text}"

            # Create reroll view
            view = RerollView(self, message, response_text)

            sent_message = None
            if is_spoilered:
                # Send response as a DM to the user
                try:
                    user = message.author
                    dm_channel = await user.create_dm()
                    async with message.channel.typing():
                        if len(prefixed_response) > 2000:
                            # Create and send markdown file
                            file = await self.create_response_file(prefixed_response, str(message.id))
                            sent_message = await dm_channel.send(
                                f"[{self.name}] Response was too long. Full response is in the attached file:",
                                file=file,
                                view=view
                            )
                        else:
                            sent_message = await dm_channel.send(prefixed_response, view=view)
                except discord.Forbidden:
                    logging.warning(f"Cannot send DM to user {message.author}")
                    can_dm = False

            if not is_spoilered or (is_spoilered and not can_dm and can_send):
                async with message.channel.typing():
                    if len(prefixed_response) > 2000:
                        # Create and send markdown file
                        file = await self.create_response_file(prefixed_response, str(message.id))
                        sent_message = await message.reply(
                            f"[{self.name}] Response was too long. Full response is in the attached file:",
                            file=file,
                            view=view
                        )
                    else:
                        sent_message = await message.reply(prefixed_response, view=view)

            # Add reaction based on emotion analysis
            try:
                if permissions.add_reactions:
                    emotion = analyze_emotion(response_text)
                    if emotion:
                        await message.add_reaction(emotion)
            except Exception as e:
                logging.error(f"Error adding emotion reaction: {str(e)}")

            return sent_message

        except Exception as e:
            logging.error(f"Error sending response for {self.name}: {str(e)}")
            try:
                if permissions.add_reactions:
                    await message.add_reaction('❌')
            except:
                pass
            return None

    async def handle_message(self, message):
        """Handle incoming messages - this is called by the bot's on_message event"""
        if message.author == bot.user:
            return

        # Process images first if there are any attachments
        if message.attachments:
            image_attachments = [
                att for att in message.attachments 
                if att.content_type and att.content_type.startswith('image/')
            ]
            if image_attachments:
                # Get Llama cog for vision processing
                llama_cog = self.bot.get_cog('Llama-3.2-11B')
                if llama_cog and llama_cog.supports_vision:
                    await self.process_images(message)
                    # Return if this is not the Llama cog (let other models wait for alt text)
                    if self.name != "Llama-3.2-11B":
                        return

        # Check if message triggers this cog
        msg_content = message.content.lower()
        is_triggered = any(word in msg_content for word in self.trigger_words)

        if is_triggered:
            logging.debug(f"[{self.name}] Triggered by message: {message.content}")
            try:
                # Check permissions
                permissions = message.channel.permissions_for(message.guild.me if message.guild else self.bot.user)
                can_send = permissions.send_messages if hasattr(permissions, 'send_messages') else True
                can_add_reactions = permissions.add_reactions if hasattr(permissions, 'add_reactions') else True

                if not can_send:
                    logging.warning(f"[{self.name}] Missing permission to send messages in channel {message.channel.id}")
                    return

                # Generate response
                response = await self.generate_response(message)

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
                                channel_id=str(message.channel.id)  # Ensure channel_id is passed as string
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

        # Get Llama cog for vision processing
        llama_cog = self.bot.get_cog('Llama-3.2-11B')
        if not llama_cog or not llama_cog.supports_vision:
            return

        image_attachments = [
            att for att in message.attachments 
            if att.content_type and att.content_type.startswith('image/')
        ]

        if not image_attachments:
            return

        async with message.channel.typing():
            for attachment in image_attachments:
                try:
                    # Check if bot has permission to add reactions
                    if message.channel.permissions_for(message.guild.me).add_reactions:
                        await message.add_reaction('🔍')  # Processing indicator
                    
                    # Use Llama cog for vision processing
                    description = await llama_cog.generate_image_description(attachment.url)
                    
                    if description:
                        # Store alt text in database
                        success = store_alt_text(
                            message_id=str(message.id),
                            channel_id=str(message.channel.id),
                            alt_text=description,
                            attachment_url=attachment.url
                        )
                        
                        if success:
                            # Log the image description interaction
                            try:
                                log_interaction(
                                    user_id=message.author.id,
                                    guild_id=message.guild.id if message.guild else None,
                                    persona_name="Llama-Vision",
                                    user_message=f"Image URL: {attachment.url}",
                                    assistant_reply=description,
                                    channel_id=str(message.channel.id)  # Ensure channel_id is passed as string
                                )
                                logging.debug(f"[Llama-Vision] Logged image description for user {message.author.id}")
                                
                                # Replace processing indicator with success indicator
                                if message.channel.permissions_for(message.guild.me).add_reactions:
                                    await message.remove_reaction('🔍', self.bot.user)
                                    await message.add_reaction('🖼️')  # Image processed indicator
                            except Exception as e:
                                logging.error(f"[Llama-Vision] Failed to log image description: {str(e)}")
                                if message.channel.permissions_for(message.guild.me).add_reactions:
                                    await message.remove_reaction('🔍', self.bot.user)
                                    await message.add_reaction('❌')
                        else:
                            if message.channel.permissions_for(message.guild.me).add_reactions:
                                await message.remove_reaction('🔍', self.bot.user)
                                await message.add_reaction('❌')
                    else:
                        if message.channel.permissions_for(message.guild.me).add_reactions:
                            await message.remove_reaction('🔍', self.bot.user)
                            await message.add_reaction('❌')
                except Exception as e:
                    logging.error(f"[{self.name}] Failed to process image: {str(e)}")
                    if message.channel.permissions_for(message.guild.me).add_reactions:
                        await message.remove_reaction('🔍', self.bot.user)
                        await message.add_reaction('❌')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction adds to process unprocessed images"""
        # Skip bot's own reactions
        if payload.user_id == self.bot.user.id:
            return

        try:
            # Get the channel
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return

            # Get the message
            message = await channel.fetch_message(payload.message_id)
            if not message:
                return

            # Check if message has images and no alt text
            if message.attachments:
                # Process any unprocessed images
                await self.process_images(message)

        except Exception as e:
            logging.error(f"Error handling reaction: {str(e)}")

    async def generate_response(self, message):
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

            # Get last 50 messages from database
            channel_id = str(message.channel.id)
            history_messages = get_message_history(channel_id, limit=50)
            messages.extend(history_messages)

            # Add current message with any image descriptions from the database
            if message.attachments and not self.supports_vision:
                # Get alt text for this message
                alt_text = get_alt_text(str(message.id))
                if alt_text:
                    messages.append({
                        "role": "user",
                        "content": f"{message.content}\n\nImage description: {alt_text}"
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": message.content
                    })
            else:
                messages.append({
                    "role": "user",
                    "content": message.content
                })

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
