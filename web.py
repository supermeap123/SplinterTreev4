"""
Web dashboard for SplinterTree bot with configuration validation.
"""
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session, send_from_directory
import os
import sqlite3
import json
import logging
from datetime import datetime
import pytz
from functools import wraps
from contextlib import contextmanager
import secrets
from pathlib import Path
import asyncio
import discord
import sys
import requests
from bot import SplinterTreeBot, setup_cogs

def validate_config():
    """Validate configuration before starting"""
    errors = []
    warnings = []

    # Check required environment variables
    required_vars = [
        'DISCORD_TOKEN',
        'OPENROUTER_API_KEY',
        'ADMIN_USERNAME',
        'ADMIN_PASSWORD',
        'SECRET_KEY'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")

    # Test OpenRouter API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    if api_key:
        try:
            response = requests.get(
                'https://openrouter.ai/api/v1/auth/key',
                headers={'Authorization': f'Bearer {api_key}'}
            )
            if response.status_code != 200:
                errors.append(f"Invalid OpenRouter API key (Status: {response.status_code})")
        except Exception as e:
            errors.append(f"Error testing OpenRouter API key: {str(e)}")

    # Check security settings
    if os.getenv('ADMIN_PASSWORD') == 'change_me_in_production':
        warnings.append("Using default admin password")
    
    if os.getenv('DEBUG', 'false').lower() == 'true':
        warnings.append("Debug mode is enabled")

    # Check database directory
    if not os.path.exists('databases'):
        try:
            os.makedirs('databases')
        except Exception as e:
            errors.append(f"Failed to create databases directory: {str(e)}")

    # Check database initialization
    try:
        with sqlite3.connect('databases/interaction_logs.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            if not cursor.fetchall():
                errors.append("Database not initialized")
    except Exception as e:
        errors.append(f"Database error: {str(e)}")

    # Print warnings
    for warning in warnings:
        logging.warning(f"Configuration Warning: {warning}")

    # If there are errors, exit
    if errors:
        for error in errors:
            logging.error(f"Configuration Error: {error}")
        sys.exit(1)

    logging.info("Configuration validation successful")

# Create required directories
Path('databases').mkdir(exist_ok=True)
Path('logs').mkdir(exist_ok=True)
Path('static').mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/web_server.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Authentication credentials
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'change_me_in_production')

# Paths
DB_PATH = 'databases/interaction_logs.db'
CONFIG_PATH = 'bot_config.json'
STATUS_PATH = 'bot_status.txt'

# Initialize bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.typing = True
intents.dm_messages = True
intents.guilds = True
intents.members = True

bot = SplinterTreeBot(command_prefix='!', help_command=None, intents=intents)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Status configuration
STATUS_CONFIG = {
    'manual_status': None,
    'show_uptime': True,
    'last_update': 0
}

def save_status_config():
    """Save status configuration"""
    try:
        config = {
            'manual_status': STATUS_CONFIG['manual_status'],
            'show_uptime': STATUS_CONFIG['show_uptime']
        }
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        logger.error(f"Error saving status config: {e}")

def load_status_config():
    """Load status configuration"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                STATUS_CONFIG['manual_status'] = config.get('manual_status')
                STATUS_CONFIG['show_uptime'] = config.get('show_uptime', True)
    except Exception as e:
        logger.error(f"Error loading status config: {e}")

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_db_stats():
    """Get statistics from the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get total messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # Get active channels
            cursor.execute("SELECT COUNT(DISTINCT channel_id) FROM messages")
            active_channels = cursor.fetchone()[0]
            
            # Get messages today
            today = datetime.now(pytz.UTC).strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp >= ?", (today,))
            messages_today = cursor.fetchone()[0]
            
            # Get most active model
            cursor.execute(""" 
                SELECT persona_name, COUNT(*) as count 
                FROM messages 
                WHERE is_assistant = 1 AND persona_name IS NOT NULL 
                GROUP BY persona_name 
                ORDER BY count DESC 
                LIMIT 1 
            """)
            result = cursor.fetchone()
            most_active_model = result[0] if result else "N/A"
            
            # Get recent activity
            cursor.execute(""" 
                SELECT timestamp, content, is_assistant, persona_name 
                FROM messages 
                ORDER BY timestamp DESC 
                LIMIT 10 
            """)
            recent = cursor.fetchall()
            recent_activity = []
            
            for row in recent:
                timestamp = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
                content = row[1]
                is_assistant = row[2]
                persona_name = row[3]
                
                if is_assistant:
                    activity = f"[{persona_name}] {content}"
                else:
                    activity = f"[User] {content}"
                
                recent_activity.append({
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'content': activity
                })
            
            return {
                'total_messages': total_messages,
                'active_channels': active_channels,
                'messages_today': messages_today,
                'most_active_model': most_active_model,
                'recent_activity': recent_activity,
                'current_time': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
            }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            'total_messages': 0,
            'active_channels': 0,
            'messages_today': 0,
            'most_active_model': 'N/A',
            'recent_activity': [],
            'current_time': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
        }

def login_required(f):
    """Decorator for routes that require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory('static', 'favicon.png', mimetype='image/png')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('dashboard'))
        
        return render_template_string(LOGIN_TEMPLATE, error="Invalid credentials")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Handle logout"""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Render the dashboard"""
    try:
        stats = get_db_stats()
        return render_template_string(open('static/dashboard.html').read(), 
                                    stats=stats,
                                    recent_activity=stats['recent_activity'],
                                    current_time=stats['current_time'],
                                    show_uptime=STATUS_CONFIG['show_uptime'],
                                    manual_status=STATUS_CONFIG['manual_status'])
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        return "Internal Server Error", 500

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Handle chat messages"""
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({'error': 'No message provided'}), 400

        # Get unified cog
        unified_cog = bot.get_cog('UnifiedCog')
        if not unified_cog:
            return jsonify({'error': 'UnifiedCog not available'}), 500

        # Run async code in the event loop
        async def process_message():
            # Create a mock message object
            class MockMessage:
                def __init__(self, content):
                    self.content = content
                    self.attachments = []
                    self.embeds = []
                    self.author = None
                    self.guild = None
                    self.channel = None

            mock_msg = MockMessage(message)
            
            # Determine model and generate response
            model_config = await unified_cog.determine_route(mock_msg)
            response = ""
            async for chunk in unified_cog.generate_response(mock_msg, model_config):
                response += chunk

            return {
                'response': response,
                'model': model_config['name']
            }

        result = loop.run_until_complete(process_message())
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for stats"""
    try:
        return jsonify(get_db_stats())
    except Exception as e:
        logger.error(f"Error getting API stats: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/set_status', methods=['POST'])
@login_required
def set_status():
    """Set the bot's status"""
    try:
        status = request.form.get('status')
        if not status:
            logger.error("No status provided")
            return "No status provided", 400

        STATUS_CONFIG['manual_status'] = status
        STATUS_CONFIG['last_update'] = datetime.now().timestamp()
        save_status_config()

        # Write to status file for bot to pick up
        with open(STATUS_PATH, 'w', encoding='utf-8') as f:
            f.write(status)

        logger.info(f"Bot status updated: {status}")
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error setting status: {e}")
        return "Error updating status", 500

@app.route('/api/toggle_uptime', methods=['POST'])
@login_required
def toggle_uptime():
    """Toggle uptime status display"""
    try:
        data = request.get_json()
        STATUS_CONFIG['show_uptime'] = data.get('enabled', True)
        save_status_config()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error toggling uptime: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_status', methods=['POST'])
@login_required
def clear_status():
    """Clear manual status and return to uptime display"""
    try:
        STATUS_CONFIG['manual_status'] = None
        save_status_config()
        
        # Clear status file
        with open(STATUS_PATH, 'w') as f:
            f.write('')
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error clearing status: {e}")
        return jsonify({'error': str(e)}), 500

async def init_bot():
    """Initialize the bot and load cogs"""
    try:
        await setup_cogs(bot)
        logger.info("Bot initialized and cogs loaded")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        raise

def main():
    """Main entry point with validation"""
    try:
        # Validate configuration before starting
        validate_config()
        
        # Load status configuration
        load_status_config()
        
        # Initialize bot and load cogs
        loop.run_until_complete(init_bot())
        
        # Start the Flask app
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
