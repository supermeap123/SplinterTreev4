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
        return self.temperatures.get(self.name.lower(), 0.7)'''

# Template for generate_response with fallback handling
RESPONSE_TEMPLATE = '''
    async def generate_response(self, message):
        """Generate a response using openrouter with fallback handling"""
        try:
            # Format system prompt
            formatted_prompt = self.format_prompt(message)
            messages = [{{"role": "system", "content": formatted_prompt}}]

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
                
                messages.append({{
                    "role": role,
                    "content": content
                }})

            # Add the current message
            messages.append({{
                "role": "user",
                "content": message.content
            }})

            logging.debug(f"[{log_name}] Sending {{len(messages)}} messages to API")
            logging.debug(f"[{log_name}] Formatted prompt: {{formatted_prompt}}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[{log_name}] Using temperature: {{temperature}}")

            # Get user_id and guild_id
            user_id = str(message.author.id)
            guild_id = str(message.guild.id) if message.guild else None

            # Try primary model first
            try:
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
                if response_stream:
                    return response_stream
            except Exception as e:
                logging.warning(f"Primary model failed: {{e}}")

            # Try fallback model if available
            fallback_model = "{fallback_model}"
            if fallback_model and fallback_model != self.model:
                try:
                    logging.info(f"[{log_name}] Trying fallback model: {{fallback_model}}")
                    response_stream = await self.api_client.call_openpipe(
                        messages=messages,
                        model=fallback_model,
                        temperature=temperature,
                        stream=True,
                        provider="{provider}",
                        user_id=user_id,
                        guild_id=guild_id,
                        prompt_file="{prompt_file}"
                    )
                    return response_stream
                except Exception as e:
                    logging.error(f"Fallback model failed: {{e}}")

            return None

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
    'gemini': {
        'class_name': 'GeminiCog',
        'name': 'Gemini',
        'nickname': 'Gemini',
        'trigger_words': "['gemini']",
        'model': 'google/gemini-pro-1.5-exp',
        'fallback_model': 'google/gemini-pro-1.5',
        'provider': 'openrouter',
        'prompt_file': 'gemini_prompts',
        'supports_vision': 'False',
        'log_name': 'Gemini',
        'qualified_name': 'Gemini'
    },
    'hermes': {
        'class_name': 'HermesCog',
        'name': 'Hermes',
        'nickname': 'Hermes',
        'trigger_words': "['hermes']",
        'model': 'nousresearch/hermes-3-llama-3.1-405b:free',
        'fallback_model': 'nousresearch/hermes-3-llama-3.1-405b',
        'provider': 'openrouter',
        'prompt_file': 'hermes_prompts',
        'supports_vision': 'False',
        'log_name': 'Hermes',
        'qualified_name': 'Hermes'
    },
    'llama32vision': {
        'class_name': 'Llama32VisionCog',
        'name': 'Llama-3.2-Vision',
        'nickname': 'Llama Vision',
        'trigger_words': "['llamavision', 'describe image', 'what is this image']",
        'model': 'meta-llama/llama-3.2-90b-vision-instruct:free',
        'fallback_model': 'meta-llama/llama-3.2-90b-vision-instruct',
        'provider': 'openrouter',
        'prompt_file': 'llama32_vision_prompts',
        'supports_vision': 'True',
        'log_name': 'Llama-3.2-Vision',
        'qualified_name': 'Llama-3.2-Vision'
    },
    'llama405b': {
        'class_name': 'Llama405bCog',
        'name': 'Llama-405b',
        'nickname': 'Llama',
        'trigger_words': "['llama', 'llama3']",
        'model': 'meta-llama/llama-3.1-405b-instruct:free',
        'fallback_model': 'meta-llama/llama-3.1-405b-instruct',
        'provider': 'openrouter',
        'prompt_file': 'llama405b_prompts',
        'supports_vision': 'False',
        'log_name': 'Llama-405b',
        'qualified_name': 'Llama-405b'
    },
    'ministral': {
        'class_name': 'MinistralCog',
        'name': 'Ministral',
        'nickname': 'Ministral',
        'trigger_words': "['ministral']",
        'model': 'mistralai/ministral-3b',
        'fallback_model': '',
        'provider': 'openrouter',
        'prompt_file': 'ministral_prompts',
        'supports_vision': 'False',
        'log_name': 'Ministral',
        'qualified_name': 'Ministral'
    },
    'sorcerer': {
        'class_name': 'SorcererCog',
        'name': 'Sorcerer',
        'nickname': 'Sorcerer',
        'trigger_words': "['sorcerer', 'sorcererlm']",
        'model': 'raifle/sorcererlm-8x22b',
        'fallback_model': '',
        'provider': 'openrouter',
        'prompt_file': 'sorcerer_prompts',
        'supports_vision': 'False',
        'log_name': 'Sorcerer',
        'qualified_name': 'Sorcerer'
    },
    'goliath': {
        'class_name': 'GoliathCog',
        'name': 'Goliath',
        'nickname': 'Goliath',
        'trigger_words': "['120b', 'goliath']",
        'model': 'alpindale/goliath-120b',
        'fallback_model': '',
        'provider': 'openrouter',
        'prompt_file': 'goliath_prompts',
        'supports_vision': 'False',
        'log_name': 'Goliath',
        'qualified_name': 'Goliath'
    },
    'dolphin': {
        'class_name': 'DolphinCog',
        'name': 'Dolphin',
        'nickname': 'Dolphin',
        'trigger_words': "['dolphin']",
        'model': 'cognitivecomputations/dolphin-mixtral-8x22b',
        'fallback_model': '',
        'provider': 'openrouter',
        'prompt_file': 'dolphin_prompts',
        'supports_vision': 'False',
        'log_name': 'Dolphin',
        'qualified_name': 'Dolphin'
    },
    'sonar': {
        'class_name': 'SonarCog',
        'name': 'Sonar',
        'nickname': 'Sonar',
        'trigger_words': "['sonar']",
        'model': 'perplexity/llama-3.1-sonar-small-128k-online',
        'fallback_model': 'perplexity/llama-3.1-sonar-large-128k-online',
        'provider': 'openrouter',
        'prompt_file': 'sonar_prompts',
        'supports_vision': 'False',
        'log_name': 'Sonar',
        'qualified_name': 'Sonar'
    },
    'sonnet': {
        'class_name': 'SonnetCog',
        'name': 'Sonnet',
        'nickname': 'Sonnet',
        'trigger_words': "['sonnet']",
        'model': 'anthropic/claude-3-5-sonnet:beta',
        'fallback_model': '',
        'provider': 'openrouter',
        'prompt_file': 'sonnet_prompts',
        'supports_vision': 'False',
        'log_name': 'Sonnet',
        'qualified_name': 'Sonnet'
    },
    'sydney': {
        'class_name': 'SydneyCog',
        'name': 'Sydney',
        'nickname': 'Sydney',
        'trigger_words': "['syd', 'sydney']",
        'model': 'meta-llama/llama-3.1-405b-instruct:free',
        'fallback_model': 'meta-llama/llama-3.1-405b-instruct',
        'provider': 'openrouter',
        'prompt_file': 'sydney_prompts',
        'supports_vision': 'False',
        'log_name': 'Sydney',
        'qualified_name': 'Sydney'
    }
}

def update_cog(cog_name, config):
    """Update a single cog file with the new template"""
    try:
        # Start with the base template
        cog_content = BASE_TEMPLATE.format(**config)

        # Add the response template
        cog_content += RESPONSE_TEMPLATE.format(
            provider=config['provider'],
            log_name=config['log_name'],
            name=config['name'],
            prompt_file=config['prompt_file'],
            fallback_model=config.get('fallback_model', '')
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
