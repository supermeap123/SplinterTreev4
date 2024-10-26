import discord
from discord.ext import commands
import json
import logging
import os
from datetime import datetime
from shared.utils import analyze_emotion
from shared.api import api

class BaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_message(self, ctx, content):
        if content.strip() == "":
            content = "I apologize, but I don't have a response for that."
        await ctx.send(content)

    async def send_embed(self, ctx, embed):
        await ctx.send(embed=embed)

    async def send_image(self, ctx, image_url):
        embed = discord.Embed()
        embed.set_image(url=image_url)
        await self.send_embed(ctx, embed)

    async def process_response(self, ctx, response):
        if isinstance(response, str):
            await self.send_message(ctx, response)
        elif isinstance(response, discord.Embed):
            await self.send_embed(ctx, response)
        elif isinstance(response, dict):
            if "type" in response:
                if response["type"] == "image":
                    await self.send_image(ctx, response["url"])
                else:
                    await self.send_message(ctx, str(response))
            else:
                await self.send_message(ctx, str(response))
        else:
            await self.send_message(ctx, str(response))

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

    async def process_message(self, message, context=None):
        """Process message and generate response"""
        try:
            # Format system prompt with dynamic variables
            formatted_prompt = self.raw_prompt.format(
                discord_user=message.author.display_name,
                discord_user_id=message.author.id,
                local_time=datetime.now().strftime("%I:%M %p"),
                local_timezone="UTC",  # Could be made dynamic if needed
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

            logging.debug(f"[{self.name}] Formatted prompt: {formatted_prompt}")
            if dynamic_prompt:
                logging.debug(f"[{self.name}] Added dynamic prompt: {dynamic_prompt}")

            # Add user message
            messages.append({
                "role": "user",
                "content": message.content
            })

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
