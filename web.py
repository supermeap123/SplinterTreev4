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

# Create required directories before configuring logging
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

# Authentication credentials - should be set via environment variables in production
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'change_me_in_production')

# Database path
DB_PATH = 'databases/interaction_logs.db'
CONFIG_PATH = 'bot_config.json'
STATUS_PATH = 'bot_status.txt'

# Login page template with improved styling and security
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SplinterTree Login</title>
    <link rel="icon" type="image/png" href="/static/favicon.png">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .login-container {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
            margin: 1rem;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 2rem;
        }
        .form-group {
            margin-bottom: 1rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #34495e;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
            transition: border-color 0.3s;
            box-sizing: border-box;
        }
        input[type="text"]:focus,
        input[type="password"]:focus {
            border-color: #3498db;
            outline: none;
            box-shadow: 0 0 0 2px rgba(52,152,219,0.2);
        }
        button {
            width: 100%;
            padding: 0.75rem;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #2980b9;
        }
        .error {
            color: #e74c3c;
            text-align: center;
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🌳 SplinterTree</h1>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="post" action="/login">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required autocomplete="current-password">
            </div>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""

# Dashboard template remains unchanged
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SplinterTree Dashboard</title>
    <link rel="icon" type="image/png" href="/static/favicon.png">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border: 1px solid #eee;
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            color: #34495e;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }
        .recent-activity {
            margin-top: 30px;
        }
        .activity-item {
            padding: 15px;
            border-bottom: 1px solid #eee;
        }
        .activity-item:last-child {
            border-bottom: none;
        }
        .timestamp {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        .refresh-text {
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 20px;
        }
        .status-form {
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .status-form input[type="text"] {
            width: calc(100% - 22px);
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .status-form button {
            background: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
        }
        .status-form button:hover {
            background: #2980b9;
        }
        .toggle-container {
            display: flex;
            align-items: center;
            margin: 10px 0;
        }
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 60px;
            height: 34px;
            margin-right: 10px;
        }
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: .4s;
            border-radius: 34px;
        }
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 26px;
            width: 26px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }
        input:checked + .toggle-slider {
            background-color: #2196F3;
        }
        input:checked + .toggle-slider:before {
            transform: translateX(26px);
        }
        .logout-link {
            position: absolute;
            top: 20px;
            right: 20px;
            color: #666;
            text-decoration: none;
            padding: 8px 16px;
            background: #f8f9fa;
            border-radius: 4px;
            transition: all 0.3s;
        }
        .logout-link:hover {
            color: #333;
            background: #e9ecef;
        }
        @media (max-width: 600px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('total-messages').textContent = data.total_messages;
                    document.getElementById('active-channels').textContent = data.active_channels;
                    document.getElementById('messages-today').textContent = data.messages_today;
                    document.getElementById('most-active-model').textContent = data.most_active_model;

                    const activityContainer = document.getElementById('recent-activity-container');
                    activityContainer.innerHTML = '';
                    data.recent_activity.forEach(activity => {
                        const div = document.createElement('div');
                        div.className = 'activity-item';
                        div.innerHTML = `
                            <span class="timestamp">${activity.timestamp}</span>
                            <br>
                            ${activity.content}
                        `;
                        activityContainer.appendChild(div);
                    });

                    document.getElementById('last-update').textContent = data.current_time;
                });
        }

        setInterval(updateStats, 5000);

        function toggleUptimeStatus() {
            const checked = document.getElementById('uptime-toggle').checked;
            fetch('/api/toggle_uptime', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    enabled: checked
                })
            });
        }
    </script>
</head>
<body>
    <a href="/logout" class="logout-link">Logout</a>
    <div class="container">
        <h1>🌳 SplinterTree Dashboard</h1>
        
        <div class="status-form">
            <h3>Bot Status Control</h3>
            <div class="toggle-container">
                <label class="toggle-switch">
                    <input type="checkbox" id="uptime-toggle" onchange="toggleUptimeStatus()" {{ 'checked' if uptime_enabled else '' }}>
                    <span class="toggle-slider"></span>
                </label>
                <span>Show Uptime in Status</span>
            </div>
            <form action="/set_status" method="POST">
                <input type="text" name="status" placeholder="Enter new bot status..." required>
                <button type="submit">Update Status</button>
            </form>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Messages</h3>
                <div class="stat-value" id="total-messages">{{ stats.total_messages }}</div>
            </div>
            <div class="stat-card">
                <h3>Active Channels</h3>
                <div class="stat-value" id="active-channels">{{ stats.active_channels }}</div>
            </div>
            <div class="stat-card">
                <h3>Messages Today</h3>
                <div class="stat-value" id="messages-today">{{ stats.messages_today }}</div>
            </div>
            <div class="stat-card">
                <h3>Most Active Model</h3>
                <div class="stat-value" id="most-active-model">{{ stats.most_active_model }}</div>
            </div>
        </div>

        <div class="recent-activity">
            <h2>Recent Activity</h2>
            <div id="recent-activity-container">
                {% for activity in recent_activity %}
                <div class="activity-item">
                    <span class="timestamp">{{ activity.timestamp }}</span>
                    <br>
                    {{ activity.content }}
                </div>
                {% endfor %}
            </div>
        </div>

        <p class="refresh-text">Stats auto-update every 5 seconds. Last updated: <span id="last-update">{{ current_time }}</span></p>
    </div>
</body>
</html>
"""

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
    """Get statistics from the database with error handling"""
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

def get_uptime_enabled():
    """Get uptime status toggle state with error handling"""
    try:
        if not Path(CONFIG_PATH).exists():
            save_uptime_enabled(True)
            logger.info("Created default config")
        
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            return config.get('uptime_enabled', True)
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return True

def save_uptime_enabled(enabled):
    """Save uptime status toggle state with error handling"""
    try:
        config = {'uptime_enabled': enabled}
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
        logger.info(f"Uptime status updated: {enabled}")
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise

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
    """Handle login with improved security"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session.permanent = True  # Make session persistent
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
        uptime_enabled = get_uptime_enabled()
        return render_template_string(DASHBOARD_TEMPLATE, 
                                    stats=stats,
                                    recent_activity=stats['recent_activity'],
                                    current_time=stats['current_time'],
                                    uptime_enabled=uptime_enabled)
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        return "Internal Server Error", 500

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
    """Set the bot's status with proper file handling"""
    try:
        status = request.form.get('status')
        if not status:
            logger.error("No status provided")
            return "No status provided", 400

        # Ensure the status file directory exists
        status_dir = os.path.dirname(STATUS_PATH)
        if status_dir and not os.path.exists(status_dir):
            os.makedirs(status_dir, exist_ok=True)
            logger.info(f"Created status directory: {status_dir}")

        # Write status atomically using a temporary file
        temp_path = f"{STATUS_PATH}.tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(status)
            os.replace(temp_path, STATUS_PATH)
            logger.info(f"Bot status updated: {status}")
            return redirect(url_for('dashboard'))
        except Exception as e:
            logger.error(f"Error writing status file: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise
    except Exception as e:
        logger.error(f"Error setting status: {e}")
        return "Error updating status", 500

@app.route('/api/toggle_uptime', methods=['POST'])
@login_required
def toggle_uptime():
    """Toggle uptime status display with error handling"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        save_uptime_enabled(enabled)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error toggling uptime: {e}")
        return jsonify({'error': str(e)}), 500

def main():
    """Main entry point with initialization"""
    try:
        # Create a simple tree favicon
        from PIL import Image, ImageDraw
        
        # Create favicon if it doesn't exist
        favicon_path = Path('static/favicon.png')
        if not favicon_path.exists():
            img = Image.new('RGBA', (32, 32), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw a simple tree
            draw.polygon([(16, 4), (28, 20), (4, 20)], fill='#2ecc71')  # Tree top
            draw.rectangle([14, 20, 18, 28], fill='#8b4513')  # Tree trunk
            
            img.save(favicon_path, 'PNG')
            logger.info("Created favicon")
        
        # Initialize database if needed
        if not Path(DB_PATH).exists():
            with open('databases/schema.sql', 'r') as f:
                schema_sql = f.read()
            
            with get_db_connection() as conn:
                conn.executescript(schema_sql)
                logger.info("Database initialized")
        
        # Create default config if it doesn't exist
        if not Path(CONFIG_PATH).exists():
            save_uptime_enabled(True)
            logger.info("Created default config")
        
        # Start the Flask app
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == '__main__':
    main()
