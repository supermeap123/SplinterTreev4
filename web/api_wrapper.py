import os
import logging
from openpipe import AsyncOpenAI as OpenPipeAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIWrapper:
    def __init__(self):
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self.openpipe_api_key = os.getenv('OPENPIPE_API_KEY')
        self.openpipe_api_url = os.getenv('OPENPIPE_API_URL', 'https://api.openpipe.ai/api/v1')
        
        # Initialize clients only if API keys are available
        self.openpipe_client = None
        self.openrouter_client = None
        
        if self.openpipe_api_key:
            self.openpipe_client = OpenPipeAI(
                api_key=self.openpipe_api_key,
                openpipe={
                    "api_key": self.openpipe_api_key,
                    "base_url": self.openpipe_api_url
                }
            )
        
        if self.openrouter_api_key:
            self.openrouter_client = OpenPipeAI(
                api_key=self.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1"
            )

    async def chat_completion(self, message: str, model: str, provider: str = 'openrouter') -> str:
        """Send a chat completion request to the specified provider"""
        try:
            messages = [{"role": "user", "content": message}]
            
            if provider == 'openpipe':
                if not self.openpipe_client:
                    return "OpenPipe API key not configured"
                client = self.openpipe_client
            else:
                if not self.openrouter_client:
                    return "OpenRouter API key not configured"
                client = self.openrouter_client
            
            logger.info(f"Sending request to {provider} model {model}")
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error in chat completion: {error_message}")
            if "insufficient_quota" in error_message.lower():
                return "⚠️ API credits depleted. Please check your API key configuration."
            elif "invalid_api_key" in error_message.lower():
                return "🔑 Invalid API key. Please check your configuration."
            elif "rate_limit_exceeded" in error_message.lower():
                return "⏳ Rate limit exceeded. Please try again later."
            else:
                return f"Error: {error_message}"

    def list_models(self, provider: str = None) -> list:
        """List available models for the specified provider"""
        openrouter_models = [
            'anthropic/claude-3-opus',
            'anthropic/claude-3-sonnet',
            'anthropic/claude-2',
            'anthropic/claude-1.1',
            'google/gemini-pro',
            'xai/grok-1',
            'nousresearch/hermes',
            'meta-llama/llama-3.2-11b',
            'anthropic/magnum',
            'mistralai/mistral-7b',
            'gryphe/mythomax',
            'nvidia/nemotron',
            'neversleep/noromaid',
            'openai/o1-mini',
            'openchat/openchat',
            'cohere/command-r-plus',
            'perplexity/sonar'
        ]
        
        openpipe_models = ['sydney']
        
        if provider == 'openrouter':
            return openrouter_models
        elif provider == 'openpipe':
            return openpipe_models
        else:
            return {
                'openrouter': openrouter_models,
                'openpipe': openpipe_models
            }
