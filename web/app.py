import os
import logging
from quart import Quart, render_template, request, jsonify, Response
from web.api_wrapper import APIWrapper
import sqlite3  # Import sqlite3

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
        {'id': 'anthropic/claude-3-opus:beta', 'name': 'Claude 3 Opus', 'provider': 'anthropic'},
        {'id': 'anthropic/claude-3.5-sonnet:beta', 'name': 'Claude 3 Sonnet', 'provider': 'anthropic'},
        {'id': 'anthropic/claude-2', 'name': 'Claude 2', 'provider': 'anthropic'},
        {'id': 'anthropic/claude-instant-1.1', 'name': 'Claude 1.1', 'provider': 'anthropic'},
        {'id': 'google/gemini-pro-1.5', 'name': 'Gemini Pro', 'provider': 'google'},
        {'id': 'x-ai/grok-beta', 'name': 'Grok', 'provider': 'xai'},
        {'id': 'nousresearch/hermes-3-llama-3.1-405b:free', 'name': 'Hermes', 'provider': 'nousresearch'},
        {'id': 'meta-llama/llama-3.2-11b-vision-instruct:free', 'name': 'Llama 3.2 11B', 'provider': 'meta'},
        {'id': 'anthracite-org/magnum-v4-72b', 'name': 'Magnum', 'provider': 'anthropic'},
        {'id': 'mistralai/ministral-8b', 'name': 'Ministral', 'provider': 'mistral'},
        {'id': 'gryphe/mythomax-l2-13b', 'name': 'MythoMax', 'provider': 'gryphe'},
        {'id': 'nvidia/llama-3.1-nemotron-70b-instruct', 'name': 'Nemotron', 'provider': 'nvidia'},
        {'id': 'neversleep/noromaid-20b', 'name': 'NoroMaid', 'provider': 'neversleep'},
        {'id': 'openai/o1-mini', 'name': 'O1 Mini', 'provider': 'openai'},
        {'id': 'openchat/openchat-7b:free', 'name': 'OpenChat', 'provider': 'openchat'},
        {'id': 'cohere/command-r-plus', 'name': 'Command-R Plus', 'provider': 'cohere'},
        {'id': 'perplexity/llama-3.1-sonar-huge-128k-online', 'name': 'Sonar', 'provider': 'perplexity'}
    ],
    'openpipe': [
        {'id': 'openpipe:Sydney-Court', 'name': 'Sydney Court', 'provider': 'openpipe'}
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
        image_url = data.get('image_url')
        
        logger.info(f"Chat request: model={model_id}, provider={provider}")
        
        # Add image URL to message if provided
        if image_url:
            message = f"[Image: {image_url}]\n\n{message}"
        
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


@app.route('/api/stats')
async def stats():
    try:
        conn = sqlite3.connect('messages.db')  # Connect to the database
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages")  # Execute the query
        total_messages = cursor.fetchone()[0]
        conn.close()  # Close the connection
        return jsonify({'totalMessages': total_messages})
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': 'Error fetching stats'}), 500

def create_app():
    return app
