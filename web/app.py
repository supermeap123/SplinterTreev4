import os
from quart import Quart, render_template, request, jsonify
from flask_cors import CORS
from web.api_wrapper import APIWrapper

app = Quart(__name__)
CORS(app)
api = APIWrapper()

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

@app.route('/')
async def index():
    return await render_template('index.html', models=AVAILABLE_MODELS)

@app.route('/api/models')
async def list_models():
    """List all available models"""
    return jsonify(AVAILABLE_MODELS)

@app.route('/api/chat', methods=['POST'])
async def chat():
    """Handle chat requests"""
    data = await request.get_json()
    message = data.get('message', '')
    model_id = data.get('model', 'anthropic/claude-2')
    provider = data.get('provider', 'openrouter')
    
    try:
        response = await api.chat_completion(message, model_id, provider)
        return jsonify({
            'response': response,
            'model': model_id,
            'provider': provider
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_app():
    return app
