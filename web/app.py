import os
import logging
from quart import Quart, render_template, request, jsonify, Response
from web.api_wrapper import APIWrapper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)

# Initialize API wrapper
try:
    api = APIWrapper()
    logger.info("API wrapper initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize API wrapper: {e}")
    api = None

# Available models with display names
AVAILABLE_MODELS = {
    'openrouter': [
        {'id': 'anthropic/claude-3-opus', 'name': 'Claude 3 Opus', 'provider': 'anthropic'},
        {'id': 'anthropic/claude-3-sonnet', 'name': 'Claude 3 Sonnet', 'provider': 'anthropic'},
        {'id': 'anthropic/claude-2', 'name': 'Claude 2', 'provider': 'anthropic'},
        {'id': 'anthropic/claude-1.1', 'name': 'Claude 1.1', 'provider': 'anthropic'},
        {'id': 'google/gemini-pro', 'name': 'Gemini Pro', 'provider': 'google'},
        {'id': 'xai/grok-1', 'name': 'Grok', 'provider': 'xai'},
        {'id': 'nousresearch/hermes', 'name': 'Hermes', 'provider': 'nousresearch'},
        {'id': 'meta-llama/llama-3.2-11b', 'name': 'Llama 3.2 11B', 'provider': 'meta'},
        {'id': 'anthropic/magnum', 'name': 'Magnum', 'provider': 'anthropic'},
        {'id': 'mistralai/mistral-7b', 'name': 'Ministral', 'provider': 'mistral'},
        {'id': 'gryphe/mythomax', 'name': 'MythoMax', 'provider': 'gryphe'},
        {'id': 'nvidia/nemotron', 'name': 'Nemotron', 'provider': 'nvidia'},
        {'id': 'neversleep/noromaid', 'name': 'NoroMaid', 'provider': 'neversleep'},
        {'id': 'openai/o1-mini', 'name': 'O1 Mini', 'provider': 'openai'},
        {'id': 'openchat/openchat', 'name': 'OpenChat', 'provider': 'openchat'},
        {'id': 'cohere/command-r-plus', 'name': 'Command-R Plus', 'provider': 'cohere'},
        {'id': 'perplexity/sonar', 'name': 'Sonar', 'provider': 'perplexity'}
    ],
    'openpipe': [
        {'id': 'sydney', 'name': 'Sydney', 'provider': 'openpipe'}
    ]
}

def add_cors_headers(response):
    """Add CORS headers to response"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.after_request
async def after_request(response):
    """Add CORS headers after each request"""
    return add_cors_headers(response)

@app.route('/options', methods=['OPTIONS'])
async def handle_options():
    """Handle OPTIONS requests for CORS"""
    return add_cors_headers(Response(''))

@app.route('/')
async def index():
    try:
        logger.info("Rendering index page")
        return await render_template('index.html', models=AVAILABLE_MODELS)
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/models')
async def list_models():
    """List all available models"""
    return jsonify(AVAILABLE_MODELS)

@app.route('/api/chat', methods=['POST'])
async def chat():
    """Handle chat requests"""
    if not api:
        return jsonify({'error': 'API not properly initialized'}), 500

    try:
        data = await request.get_json()
        message = data.get('message', '')
        model_id = data.get('model', 'anthropic/claude-2')
        provider = data.get('provider', 'openrouter')
        
        logger.info(f"Chat request: model={model_id}, provider={provider}")
        response = await api.chat_completion(message, model_id, provider)
        
        return jsonify({
            'response': response,
            'model': model_id,
            'provider': provider
        })
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
async def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'api_initialized': api is not None,
        'openrouter_configured': bool(os.getenv('OPENROUTER_API_KEY')),
        'openpipe_configured': bool(os.getenv('OPENPIPE_API_KEY'))
    })

def create_app():
    return app
