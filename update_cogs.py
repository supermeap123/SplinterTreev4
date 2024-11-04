import os
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)

# Template for cog files that inherit from base_cog.py
COG_TEMPLATE = '''import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

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
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[{log_name}] Initialized with raw_prompt: {{self.raw_prompt}}")
        logging.debug(f"[{log_name}] Using provider: {{self.provider}}")
        logging.debug(f"[{log_name}] Vision support: {{self.supports_vision}}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "{qualified_name}"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = {class_name}(bot)
        await bot.add_cog(cog)
        logging.info(f"[{log_name}] Registered cog with qualified_name: {{cog.qualified_name}}")
        return cog
    except Exception as e:
        logging.error(f"[{log_name}] Failed to register cog: {{str(e)}}", exc_info=True)
        raise'''

# Configuration for each cog
COGS_CONFIG = {
    'hermes': {
        'class_name': 'HermesCog',
        'name': 'Hermes-3',
        'nickname': 'Hermes',
        'trigger_words': "['hermes', 'nous', 'hermes 3']",
        'model': 'nousresearch/hermes-3-llama-3.1-405b',
        'provider': 'openrouter',
        'prompt_file': 'hermes',
        'supports_vision': 'False',
        'log_name': 'Hermes-3',
        'qualified_name': 'Hermes-3'
    },
    'moa': {
        'class_name': 'MOACog',
        'name': 'MOA',
        'nickname': 'MOA',
        'trigger_words': "['moa']",
        'model': 'openpipe:moa-gpt-4o-v1',
        'provider': 'openpipe',
        'prompt_file': None,
        'supports_vision': 'False',
        'log_name': 'MOA',
        'qualified_name': 'MOA'
    },
    'claude3opus': {
        'class_name': 'Claude3OpusCog',
        'name': 'Claude-3-Opus',
        'nickname': 'Claude',
        'trigger_words': "['claude3opus', 'opus', 'claude 3 opus']",
        'model': 'anthropic/claude-3-opus:beta',
        'provider': 'openrouter',
        'prompt_file': 'claude',
        'supports_vision': 'True',
        'log_name': 'Claude-3-Opus',
        'qualified_name': 'Claude-3-Opus'
    },
    'claude3sonnet': {
        'class_name': 'Claude3SonnetCog',
        'name': 'Claude-3-Sonnet',
        'nickname': 'Sonnet',
        'trigger_words': "['claude3sonnet', 'sonnet', 'claude 3 sonnet']",
        'model': 'anthropic/claude-3.5-sonnet:beta',
        'provider': 'openrouter',
        'prompt_file': 'claude',
        'supports_vision': 'True',
        'log_name': 'Claude-3-Sonnet',
        'qualified_name': 'Claude-3-Sonnet'
    },
    'gemini': {
        'class_name': 'GeminiCog',
        'name': 'Gemini',
        'nickname': 'Gemini',
        'trigger_words': "['gemini']",
        'model': 'google/gemini-pro-1.5',
        'provider': 'openrouter',
        'prompt_file': 'gemini',
        'supports_vision': 'True',
        'log_name': 'Gemini',
        'qualified_name': 'Gemini'
    },
    'geminipro': {
        'class_name': 'GeminiProCog',
        'name': 'Gemini-Pro',
        'nickname': 'GeminiPro',
        'trigger_words': "['geminipro', 'gemini pro']",
        'model': 'google/gemini-pro-1.5',
        'provider': 'openrouter',
        'prompt_file': 'gemini',
        'supports_vision': 'True',
        'log_name': 'Gemini-Pro',
        'qualified_name': 'Gemini-Pro'
    },
    'gemma': {
        'class_name': 'GemmaCog',
        'name': 'Gemma',
        'nickname': 'Gemma',
        'trigger_words': "['gemma']",
        'model': 'google/gemma-2-27b-it',
        'provider': 'openrouter',
        'prompt_file': 'gemma',
        'supports_vision': 'False',
        'log_name': 'Gemma',
        'qualified_name': 'Gemma'
    },
    'grok': {
        'class_name': 'GrokCog',
        'name': 'Grok',
        'nickname': 'Grok',
        'trigger_words': "['grok']",
        'model': 'x-ai/grok-beta',
        'provider': 'openrouter',
        'prompt_file': 'grok',
        'supports_vision': 'False',
        'log_name': 'Grok',
        'qualified_name': 'Grok'
    },
    'hermes': {
        'class_name': 'HermesCog',
        'name': 'Hermes',
        'nickname': 'Hermes',
        'trigger_words': "['hermes']",
        'model': 'nousresearch/hermes-3-llama-3.1-405b',
        'provider': 'openrouter',
        'prompt_file': 'hermes',
        'supports_vision': 'False',
        'log_name': 'Hermes',
        'qualified_name': 'Hermes'
    },
    'liquid': {
        'class_name': 'LiquidCog',
        'name': 'Liquid',
        'nickname': 'Liquid',
        'trigger_words': "['liquid']",
        'model': 'liquid/lfm-40b',
        'provider': 'openrouter',
        'prompt_file': 'liquid',
        'supports_vision': 'False',
        'log_name': 'Liquid',
        'qualified_name': 'Liquid'
    },
    'llama32_11b': {
        'class_name': 'Llama32_11bCog',
        'name': 'Llama-3.2-11b',
        'nickname': 'Llama',
        'trigger_words': "['llama32', 'llama 32', 'llama']",
        'model': 'meta-llama/llama-3.2-11b-vision-instruct',
        'provider': 'openrouter',
        'prompt_file': 'llama',
        'supports_vision': 'True',
        'log_name': 'Llama-3.2-11b',
        'qualified_name': 'Llama-3.2-11b'
    },
    'magnum': {
        'class_name': 'MagnumCog',
        'name': 'Magnum',
        'nickname': 'Magnum',
        'trigger_words': "['magnum']",
        'model': 'anthracite-org/magnum-v4-72b',
        'provider': 'openrouter',
        'prompt_file': 'magnum',
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
        'prompt_file': 'ministral',
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
        'prompt_file': 'nemotron',
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
        'prompt_file': 'noromaid',
        'supports_vision': 'False',
        'log_name': 'Noromaid',
        'qualified_name': 'Noromaid'
    },
    'o1mini': {
        'class_name': 'O1MiniCog',
        'name': 'O1-Mini',
        'nickname': 'O1Mini',
        'trigger_words': "['o1mini', 'o1 mini']",
        'model': 'openai/o1-mini',
        'provider': 'openrouter',
        'prompt_file': 'o1mini',
        'supports_vision': 'False',
        'log_name': 'O1-Mini',
        'qualified_name': 'O1-Mini'
    },
    'openchat': {
        'class_name': 'OpenChatCog',
        'name': 'OpenChat',
        'nickname': 'OpenChat',
        'trigger_words': "['openchat']",
        'model': 'openchat/openchat-7b',
        'provider': 'openrouter',
        'prompt_file': 'openchat',
        'supports_vision': 'False',
        'log_name': 'OpenChat',
        'qualified_name': 'OpenChat'
    },
    'rplus': {
        'class_name': 'RPlusCog',
        'name': 'R-Plus',
        'nickname': 'RPlus',
        'trigger_words': "['rplus', 'r plus']",
        'model': 'cohere/command-r-plus',
        'provider': 'openrouter',
        'prompt_file': 'rplus',
        'supports_vision': 'False',
        'log_name': 'R-Plus',
        'qualified_name': 'R-Plus'
    },
    'sonar': {
        'class_name': 'SonarCog',
        'name': 'Sonar',
        'nickname': 'Sonar',
        'trigger_words': "['sonar']",
        'model': 'perplexity/llama-3.1-sonar-huge-128k-online',
        'provider': 'openrouter',
        'prompt_file': 'sonar',
        'supports_vision': 'False',
        'log_name': 'Sonar',
        'qualified_name': 'Sonar'
    },
    'mythomax': {
        'class_name': 'MythomaxCog',
        'name': 'Mythomax',
        'nickname': 'Mythomax',
        'trigger_words': "['mythomax']",
        'model': 'gryphe/mythomax-l2-13b',
        'provider': 'openrouter',
        'prompt_file': 'mythomax',
        'supports_vision': 'False',
        'log_name': 'Mythomax',
        'qualified_name': 'Mythomax'
    }
}

def update_cog(cog_name, config):
    """Update a single cog file with the new template"""
    try:
        # Format the template with the cog's configuration
        cog_content = COG_TEMPLATE.format(**config)
        
        # Write to the cog file
        cog_path = f'cogs/{cog_name}_cog.py'
        with open(cog_path, 'w') as f:
            f.write(cog_content)
        logging.info(f"Updated {cog_path}")
        
    except Exception as e:
        logging.error(f"Error updating {cog_name}: {str(e)}")

def main():
    """Update all cogs with the new template"""
    logging.info("Starting cog updates...")
    
    # Update each cog
    for cog_name, config in COGS_CONFIG.items():
        update_cog(cog_name, config)
    
    logging.info("Cog updates completed")

if __name__ == "__main__":
    main()
