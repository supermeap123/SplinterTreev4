from flask import Flask, render_template, request, jsonify
import sys
import os

# Add the parent directory to sys.path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.api import OpenPipeAPI, OpenRouterAPI
from config import Config

app = Flask(__name__)

# Initialize APIs with test credentials
config = Config()
openpipe_api = OpenPipeAPI(config)
openrouter_api = OpenRouterAPI(config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/models')
def list_models():
    """List all available models"""
    models = {
        'openpipe': openpipe_api.list_models(),
        'openrouter': openrouter_api.list_models()
    }
    return jsonify(models)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    data = request.json
    message = data.get('message', '')
    model = data.get('model', 'claude-2')
    provider = data.get('provider', 'openrouter')
    
    try:
        if provider == 'openpipe':
            response = openpipe_api.chat_completion(message, model)
        else:
            response = openrouter_api.chat_completion(message, model)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
