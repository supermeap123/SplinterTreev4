from flask import Flask, render_template, request, jsonify
import sys
import os
from dotenv import load_dotenv

# Add the parent directory to sys.path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.api import OpenPipeAPI, OpenRouterAPI
from config import Config
from shared.utils import get_current_time_pst

# Load environment variables
load_dotenv()

app = Flask(__name__)
config = Config()

# Initialize APIs
openpipe_api = OpenPipeAPI(config)
openrouter_api = OpenRouterAPI(config)

# Available models from cogs
AVAILABLE_MODELS = {
    'openrouter': [
        {'id': 'claude-3-opus', 'name': 'Claude 3 Opus', 'provider': 'anthropic'},
        {'id': 'claude-3-sonnet', 'name': 'Claude 3 Sonnet', 'provider': 'anthropic'},
        {'id': 'claude-2', 'name': 'Claude 2', 'provider': 'anthropic'},
        {'id': 'claude-1-1', 'name': 'Claude 1.1', 'provider': 'anthropic'},
        {'id': 'gemini-pro', 'name': 'Gemini Pro', 'provider': 'google'},
        {'id': 'grok', 'name': 'Grok', 'provider': 'xai'},
        {'id': 'hermes', 'name': 'Hermes', 'provider': 'nousresearch'},
        {'id': 'llama-3-2-11b', 'name': 'Llama 3.2 11B', 'provider': 'meta'},
        {'id': 'magnum', 'name': 'Magnum', 'provider': 'anthropic'},
        {'id': 'ministral', 'name': 'Ministral', 'provider': 'mistral'},
        {'id': 'mythomax', 'name': 'MythoMax', 'provider': 'gryphe'},
        {'id': 'nemotron', 'name': 'Nemotron', 'provider': 'nvidia'},
        {'id': 'noromaid', 'name': 'NoroMaid', 'provider': 'neversleep'},
        {'id': 'o1-mini', 'name': 'O1 Mini', 'provider': 'openai'},
        {'id': 'openchat', 'name': 'OpenChat', 'provider': 'openchat'},
        {'id': 'rplus', 'name': 'Command-R Plus', 'provider': 'cohere'},
        {'id': 'sonar', 'name': 'Sonar', 'provider': 'perplexity'}
    ],
    'openpipe': [
        {'id': 'sydney', 'name': 'Sydney', 'provider': 'openpipe'}
    ]
}

@app.route('/')
def index():
    return render_template('index.html', models=AVAILABLE_MODELS)

@app.route('/api/models')
def list_models():
    """List all available models"""
    return jsonify(AVAILABLE_MODELS)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    data = request.json
    message = data.get('message', '')
    model_id = data.get('model', 'claude-2')
    provider = data.get('provider', 'openrouter')
    
    try:
        # Add context information
        current_time = get_current_time_pst()
        context = f"Current time: {current_time} PST\n\n"
        
        # Handle image URLs if present
        image_url = data.get('image_url')
        if image_url:
            context += f"[Image URL: {image_url}]\n\n"
        
        # Combine context and message
        full_message = context + message
        
        if provider == 'openpipe':
            response = openpipe_api.chat_completion(full_message, model_id)
        else:
            response = openrouter_api.chat_completion(full_message, model_id)
            
        return jsonify({
            'response': response,
            'model': model_id,
            'provider': provider,
            'timestamp': current_time
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
