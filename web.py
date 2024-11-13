from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
import os
import sqlite3
import json
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

# HTML template with embedded CSS
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SplinterTree Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
                    // Update statistics
                    document.getElementById('total-messages').textContent = data.total_messages;
                    document.getElementById('active-channels').textContent = data.active_channels;
                    document.getElementById('messages-today').textContent = data.messages_today;
                    document.getElementById('most-active-model').textContent = data.most_active_model;

                    // Update recent activity
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

                    // Update last refresh time
                    document.getElementById('last-update').textContent = data.current_time;
                });
        }

        // Update stats every 5 seconds
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

def get_db_stats():
    """Get statistics from the database"""
    try:
        conn = sqlite3.connect('databases/interaction_logs.db')
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
        
        conn.close()
        
        return {
            'total_messages': total_messages,
            'active_channels': active_channels,
            'messages_today': messages_today,
            'most_active_model': most_active_model,
            'recent_activity': recent_activity,
            'current_time': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            'total_messages': 0,
            'active_channels': 0,
            'messages_today': 0,
            'most_active_model': 'N/A',
            'recent_activity': [],
            'current_time': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
        }

def get_uptime_enabled():
    """Get uptime status toggle state"""
    try:
        with open('bot_config.json', 'r') as f:
            config = json.load(f)
            return config.get('uptime_enabled', True)
    except:
        return True

def save_uptime_enabled(enabled):
    """Save uptime status toggle state"""
    try:
        config = {'uptime_enabled': enabled}
        with open('bot_config.json', 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving config: {e}")

@app.route('/')
def dashboard():
    """Render the dashboard"""
    stats = get_db_stats()
    uptime_enabled = get_uptime_enabled()
    return render_template_string(DASHBOARD_TEMPLATE, 
                                stats=stats,
                                recent_activity=stats['recent_activity'],
                                current_time=stats['current_time'],
                                uptime_enabled=uptime_enabled)

@app.route('/api/stats')
def api_stats():
    """API endpoint for stats"""
    return jsonify(get_db_stats())

@app.route('/set_status', methods=['POST'])
def set_status():
    """Set the bot's status"""
    try:
        status = request.form.get('status')
        if status:
            # Write status to a file that the bot can read
            with open('bot_status.txt', 'w') as f:
                f.write(status)
    except Exception as e:
        print(f"Error setting status: {e}")
    return redirect(url_for('dashboard'))

@app.route('/api/toggle_uptime', methods=['POST'])
def toggle_uptime():
    """Toggle uptime status display"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        save_uptime_enabled(enabled)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
