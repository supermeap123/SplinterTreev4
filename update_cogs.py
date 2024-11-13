import os
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)

# Base template for all cogs
BASE_TEMPLATE = '''import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json

class {class_name}(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="{name}",
            nickname="{nickname}",
            trigger_words={trigger_words},
            model="{model}",
            provider="{provider}",
            prompt_file="{prompt_file}",
            supports_vision={supports_vision}
        )
        logging.debug(f"[{log_name}] Initialized with raw_prompt: {{self.raw_prompt}}")
        logging.debug(f"[{log_name}] Using provider: {{self.provider}}")
        logging.debug(f"[{log_name}] Vision support: {{self.supports_vision}}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[{log_name}] Failed to load temperatures.json: {{e}}")
            self.temperatures = {{}}

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "{qualified_name}"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)
'''

# Template for generate_response with vision support
VISION_RESPONSE_TEMPLATE = '''
    async def generate_response(self, message):
        """Generate a response using openrouter"""
        try:
            # Format system prompt
            formatted_prompt = self.format_prompt(message)
            messages = [{"role": "system", "content": formatted_prompt}]

            # Get last 50 messages from database, excluding current message
            channel_id = str(message.channel.id)
            history_messages = await self.context_cog.get_context_messages(
                channel_id, 
                limit=50,
                exclude_message_id=str(message.id)
            )
            
            # Format history messages with proper roles
            for msg in history_messages:
                role = "assistant" if msg['is_assistant'] else "user"
                content = msg['content']
                
                # Handle system summaries
                if msg['user_id'] == 'SYSTEM' and content.startswith('[SUMMARY]'):
                    role = "system"
                    content = content[9:].strip()  # Remove [SUMMARY] prefix
                
                messages.append({
                    "role": role,
                    "content": content
                })

            # Process current message and any images
            content = []
            has_images = False
            
            # Add any image attachments
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    has_images = True
                    content.append({
                        "type": "image_url",
                        "image_url": { "url": attachment.url }
                    })

            # Check for image URLs in embeds
            for embed in message.embeds:
                if embed.image and embed.image.url:
                    has_images = True
                    content.append({
                        "type": "image_url",
                        "image_url": { "url": embed.image.url }
                    })
                if embed.thumbnail and embed.thumbnail.url:
                    has_images = True
                    content.append({
                        "type": "image_url",
                        "image_url": { "url": embed.thumbnail.url }
                    })

            # Add the text content
            content.append({
                "type": "text",
                "text": message.content
            })

            # Add the message with multimodal content
            messages.append({
                "role": "user",
                "content": content
            })

            logging.debug(f"[{log_name}] Sending {{len(messages)}} messages to API")
            logging.debug(f"[{log_name}] Formatted prompt: {{formatted_prompt}}")
            logging.debug(f"[{log_name}] Has images: {{has_images}}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[{log_name}] Using temperature: {{temperature}}")

            # Get user_id and guild_id
            user_id = str(message.author.id)
            guild_id = str(message.guild.id) if message.guild else None

            # Call API and return the stream directly
            response_stream = await self.api_client.call_openpipe(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True,
                provider="{provider}",
                user_id=user_id,
                guild_id=guild_id,
                prompt_file="{prompt_file}"
            )

            return response_stream

        except Exception as e:
            logging.error(f"Error processing message for {name}: {{e}}")
            return None'''

# Template for generate_response without vision support but with image description
TEXT_RESPONSE_TEMPLATE = '''
    async def generate_response(self, message):
        """Generate a response using openrouter"""
        try:
            # Format system prompt
            formatted_prompt = self.format_prompt(message)
            messages = [{"role": "system", "content": formatted_prompt}]

            # Get last 50 messages from database, excluding current message
            channel_id = str(message.channel.id)
            history_messages = await self.context_cog.get_context_messages(
                channel_id, 
                limit=50,
                exclude_message_id=str(message.id)
            )
            
            # Format history messages with proper roles
            for msg in history_messages:
                role = "assistant" if msg['is_assistant'] else "user"
                content = msg['content']
                
                # Handle system summaries
                if msg['user_id'] == 'SYSTEM' and content.startswith('[SUMMARY]'):
                    role = "system"
                    content = content[9:].strip()  # Remove [SUMMARY] prefix
                
                messages.append({
                    "role": role,
                    "content": content
                })

            # Process current message and any images
            content = []
            has_images = False
            
            # Add any image attachments
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    has_images = True
                    content.append({
                        "type": "image_url",
                        "image_url": { "url": attachment.url }
                    })

            # Check for image URLs in embeds
            for embed in message.embeds:
                if embed.image and embed.image.url:
                    has_images = True
                    content.append({
                        "type": "image_url",
                        "image_url": { "url": embed.image.url }
                    })
                if embed.thumbnail and embed.thumbnail.url:
                    has_images = True
                    content.append({
                        "type": "image_url",
                        "image_url": { "url": embed.thumbnail.url }
                    })

            # Add the text content
            content.append({
                "type": "text",
                "text": "Please describe this image in detail." if has_images else message.content
            })

            # Add the message with multimodal content
            messages.append({
                "role": "user",
                "content": content
            })

            logging.debug(f"[{log_name}] Sending {{len(messages)}} messages to API")
            logging.debug(f"[{log_name}] Formatted prompt: {{formatted_prompt}}")
            logging.debug(f"[{log_name}] Has images: {{has_images}}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[{log_name}] Using temperature: {{temperature}}")

            # Get user_id and guild_id
            user_id = str(message.author.id)
            guild_id = str(message.guild.id) if message.guild else None

            # Call API and return the stream directly
            response_stream = await self.api_client.call_openpipe(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True,
                provider="{provider}",
                user_id=user_id,
                guild_id=guild_id,
                prompt_file="{prompt_file}"
            )

            return response_stream

        except Exception as e:
            logging.error(f"Error processing message for {name}: {{e}}")
            return None'''

# Template for setup function
SETUP_TEMPLATE = '''
async def setup(bot):
    try:
        cog = {class_name}(bot)
        await bot.add_cog(cog)
        logging.info(f"[{log_name}] Registered cog with qualified_name: {{cog.qualified_name}}")
        return cog
    except Exception as e:
        logging.error(f"[{log_name}] Failed to register cog: {{e}}", exc_info=True)
        raise'''

# Configuration for each cog based on OpenRouter models
COGS_CONFIG = {
    'freerouter': {
        'class_name': 'FreeRouterCog',
        'name': 'FreeRouter',
        'nickname': 'FreeRouter',
        'trigger_words': "['freerouter', 'router', 'route']",
        'model': 'openpipe:FreeRouter-v2-235',
        'provider': 'openpipe',
        'prompt_file': 'freerouter_prompts',
        'supports_vision': 'False',
        'log_name': 'FreeRouter',
        'qualified_name': 'FreeRouter'
    },
    'gemma': {
        'class_name': 'GemmaCog',
        'name': 'Gemma',
        'nickname': 'Gemma',
        'trigger_words': "['gemma']",
        'model': 'google/gemma-2-9b-it',
        'provider': 'openrouter',
        'prompt_file': 'gemma_prompts',
        'supports_vision': 'False',
        'log_name': 'Gemma',
        'qualified_name': 'Gemma'
    },
    'mixtral': {
        'class_name': 'MixtralCog',
        'name': 'Mixtral',
        'nickname': 'Mixtral',
        'trigger_words': "['mixtral']",
        'model': 'mixtral-8x7b-32768',
        'provider': 'groq',
        'prompt_file': 'mixtral_prompts',
        'supports_vision': 'False',
        'log_name': 'Mixtral',
        'qualified_name': 'Mixtral'
    },
    'management': {
        'class_name': 'ManagementCog',
        'name': 'Management',
        'nickname': 'Management',
        'trigger_words': "[]",
        'model': 'meta-llama/llama-3.1-405b-instruct',
        'provider': 'openrouter',
        'prompt_file': 'None',
        'supports_vision': 'False',
        'log_name': 'Management',
        'qualified_name': 'Management'
    },
    'claude3haiku': {
        'class_name': 'Claude3HaikuCog',
        'name': 'Claude-3-Haiku',
        'nickname': 'Haiku',
        'trigger_words': "['claude3haiku', 'haiku', 'claude 3 haiku']",
        'model': 'anthropic/claude-3-5-haiku:beta',
        'provider': 'openrouter',
        'prompt_file': 'claude_prompts',
        'supports_vision': 'True',
        'log_name': 'Claude-3-Haiku',
        'qualified_name': 'Claude-3-Haiku'
    },
    'hermes': {
        'class_name': 'HermesCog',
        'name': 'Hermes',
        'nickname': 'Hermes',
        'trigger_words': "['hermes']",
        'model': 'nousresearch/hermes-3-llama-3.1-405b',
        'provider': 'openrouter',
        'prompt_file': 'hermes_prompts',
        'supports_vision': 'False',
        'log_name': 'Hermes',
        'qualified_name': 'Hermes'
    },
    'liquid': {
        'class_name': 'LiquidCog',
        'name': 'Liquid',
        'nickname': 'Liquid',
        'trigger_words': "['liquid']",
        'model': 'liquid/lfm-40b:free',
        'provider': 'openrouter',
        'prompt_file': 'liquid_prompts',
        'supports_vision': 'False',
        'log_name': 'Liquid',
        'qualified_name': 'Liquid'
    },
    'llama32_11b': {
        'class_name': 'Llama32_11bCog',
        'name': 'Llama-3.2-11b',
        'nickname': 'Llama',
        'trigger_words': "['11b']",
        'model': 'meta-llama/llama-3.2-11b-vision-instruct',
        'provider': 'openrouter',
        'prompt_file': 'llama32_11b_prompts',
        'supports_vision': 'False',
        'log_name': 'Llama-3.2-11b',
        'qualified_name': 'Llama-3.2-11b'
    },
    'llama32_90b': {
        'class_name': 'Llama3290bVisionCog',
        'name': 'Llama-3.2-90B-Vision',
        'nickname': 'Llama Vision',
        'trigger_words': "['llamavision', 'describe image', 'what is this image', 'llama', 'llama3', 'llama 3', 'llama 3.2', 'llama3.2', '90b', 'llama 90b', 'vision']",
        'model': 'meta-llama/llama-3.2-90b-vision-instruct',
        'provider': 'openrouter',
        'prompt_file': 'llama32_90b_prompts',
        'supports_vision': 'True',
        'log_name': 'Llama-3.2-90B-Vision',
        'qualified_name': 'Llama-3.2-90B-Vision'
    },
    'magnum': {
        'class_name': 'MagnumCog',
        'name': 'Magnum',
        'nickname': 'Magnum',
        'trigger_words': "['magnum']",
        'model': 'anthracite-org/magnum-v4-72b',
        'provider': 'openrouter',
        'prompt_file': 'magnum_prompts',
        'supports_vision': 'False',
        'log_name': 'Magnum',
        'qualified_name': 'Magnum'
    },
    'ministral': {
        'class_name': 'MinistralCog',
        'name': 'Ministral',
        'nickname': 'Ministral',
        'trigger_words': "['ministral']",
        'model': 'mistralai/ministral-8b',
        'provider': 'openrouter',
        'prompt_file': 'ministral_prompts',
        'supports_vision': 'False',
        'log_name': 'Ministral',
        'qualified_name': 'Ministral'
    },
    'nemotron': {
        'class_name': 'NemotronCog',
        'name': 'Nemotron',
        'nickname': 'Nemotron',
        'trigger_words': "['nemotron']",
        'model': 'nvidia/llama-3.1-nemotron-70b-instruct',
        'provider': 'openrouter',
        'prompt_file': 'nemotron_prompts',
        'supports_vision': 'False',
        'log_name': 'Nemotron',
        'qualified_name': 'Nemotron'
    },
    'noromaid': {
        'class_name': 'NoromaidCog',
        'name': 'Noromaid',
        'nickname': 'Noromaid',
        'trigger_words': "['noromaid']",
        'model': 'neversleep/noromaid-20b',
        'provider': 'openrouter',
        'prompt_file': 'noromaid_prompts',
        'supports_vision': 'False',
        'log_name': 'Noromaid',
        'qualified_name': 'Noromaid'
    },
    'openchat': {
        'class_name': 'OpenChatCog',
        'name': 'OpenChat',
        'nickname': 'OpenChat',
        'trigger_words': "['openchat']",
        'model': 'openchat/openchat-7b:free',
        'provider': 'openrouter',
        'prompt_file': 'openchat_prompts',
        'supports_vision': 'False',
        'log_name': 'OpenChat',
        'qualified_name': 'OpenChat'
    },
    'router': {
        'class_name': 'RouterCog',
        'name': 'Router',
        'nickname': 'Router',
        'trigger_words': "[]",
        'model': 'openpipe:FreeRouter-v2-235',
        'provider': 'openpipe',
        'prompt_file': 'router',
        'supports_vision': 'False',
        'log_name': 'Router',
        'qualified_name': 'Router'
    },
    'rplus': {
        'class_name': 'RPlusCog',
        'name': 'R-Plus',
        'nickname': 'RPlus',
        'trigger_words': "['rplus', 'r plus']",
        'model': 'cohere/command-r-plus',
        'provider': 'openrouter',
        'prompt_file': 'rplus_prompts',
        'supports_vision': 'False',
        'log_name': 'R-Plus',
        'qualified_name': 'R-Plus'
    },
    'sorcerer': {
        'class_name': 'SorcererCog',
        'name': 'Sorcerer',
        'nickname': 'Sorcerer',
        'trigger_words': "['sorcerer', 'sorcererlm']",
        'model': 'raifle/sorcererlm-8x22b',
        'provider': 'openrouter',
        'prompt_file': 'sorcerer_prompts',
        'supports_vision': 'False',
        'log_name': 'Sorcerer',
        'qualified_name': 'Sorcerer'
    }
}

def update_cog(cog_name, config):
    """Update a single cog file with the new template"""
    try:
        # Start with the base template
        cog_content = BASE_TEMPLATE.format(**config)

        # Add the appropriate response template based on vision support
        if config['supports_vision'] == 'True':
            template = VISION_RESPONSE_TEMPLATE
        else:
            template = TEXT_RESPONSE_TEMPLATE

        cog_content += template.format(
            provider=config['provider'],
            log_name=config['log_name'],
            name=config['name'],
            prompt_file=config['prompt_file']
        )

        # Add the setup function
        cog_content += SETUP_TEMPLATE.format(**config)

        # Write to the cog file
        cog_path = f'cogs/{cog_name}_cog.py'
        with open(cog_path, 'w') as f:
            f.write(cog_content)
        logging.info(f"Updated {cog_path}")

    except Exception as e:
        logging.error(f"Error updating {cog_name}: {e}")

def main():
    """Update all cogs with the new template"""
    logging.info("Starting cog updates...")

    # Update each cog
    for cog_name, config in COGS_CONFIG.items():
        update_cog(cog_name, config)

    logging.info("Cog updates completed")

if __name__ == "__main__":
    main()
