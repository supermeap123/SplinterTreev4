from flask import Flask, render_template_string, request, redirect, url_for, flash
import os
import sqlite3
import json
from datetime import datetime, timedelta
import pytz
import discord
from discord.ext import commands
import asyncio

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
            width: 100%;
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
        @media (max-width: 600px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(function() {
            window.location.reload();
        }, 30000);
    </script>
</head>
<body>
    <div class="container">
        <h1>🌳 SplinterTree Dashboard</h1>
        
        <div class="status-form">
            <h3>Set Bot Status</h3>
            <form action="/set_status" method="POST">
                <input type="text" name="status" placeholder="Enter new bot status..." required>
                <button type="submit">Update Status</button>
            </form>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Messages</h3>
                <div class="stat-value">{{ stats.total_messages }}</div>
            </div>
            <div class="stat-card">
                <h3>Active Channels</h3>
                <div class="stat-value">{{ stats.active_channels }}</div>
            </div>
            <div class="stat-card">
                <h3>Messages Today</h3>
                <div class="stat-value">{{ stats.messages_today }}</div>
            </div>
            <div class="stat-card">
                <h3>Most Active Model</h3>
                <div class="stat-value">{{ stats.most_active_model }}</div>
            </div>
        </div>

        <div class="recent-activity">
            <h2>Recent Activity</h2>
            {% for activity in recent_activity %}
            <div class="activity-item">
                <span class="timestamp">{{ activity.timestamp }}</span>
                <br>
                {{ activity.content }}
            </div>
            {% endfor %}
        </div>

        <p class="refresh-text">Dashboard auto-refreshes every 30 seconds. Last updated: {{ current_time }}</p>
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

@app.route('/')
def dashboard():
    """Render the dashboard"""
    stats = get_db_stats()
    return render_template_string(DASHBOARD_TEMPLATE, stats=stats, 
                                recent_activity=stats['recent_activity'],
                                current_time=stats['current_time'])

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
