import json
import logging
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

def analyze_emotion(text):
    """
    Analyze the emotional content of text using simple keyword matching.
    Returns Discord-compatible emoji
    """
    # Define emotion keywords and corresponding Discord emojis
    emotions = {
        'joy': (['happy', 'joy', 'excited', 'great', 'wonderful', 'love', 'glad', 'yay', 'woohoo', 'hehe', 'haha'], '😄'),
        'sadness': (['sad', 'sorry', 'unfortunate', 'regret', 'miss', 'lonely', 'sigh', 'alas', 'ugh'], '😢'),
        'anger': (['angry', 'mad', 'furious', 'annoyed', 'frustrated', 'grr', 'ugh', 'argh'], '😠'),
        'fear': (['afraid', 'scared', 'worried', 'nervous', 'anxious', 'eek', 'yikes'], '😨'),
        'surprise': (['wow', 'amazing', 'incredible', 'unexpected', 'surprised', 'whoa', 'woah', 'omg', 'oh my'], '😮'),
        'neutral': (['ok', 'fine', 'alright', 'neutral', 'hmm', 'mhm'], '👍'),
        'expressive': (['*', 'moans', 'sighs', 'gasps', 'squeals', 'giggles', 'laughs', 'cries', 'screams'], '🎭')
    }
    
    # Convert text to lowercase for matching
    text = text.lower()
    
    # First check for expressive actions (usually in asterisks or explicit actions)
    if any(action in text for action in emotions['expressive'][0]):
        return emotions['expressive'][1]
    
    # Count emotion keywords
    emotion_counts = {emotion: 0 for emotion in emotions if emotion != 'expressive'}
    for emotion, (keywords, _) in emotions.items():
        if emotion != 'expressive':  # Skip expressive since we handled it above
            for keyword in keywords:
                emotion_counts[emotion] += text.count(keyword)
    
    # Find emotion with highest count
    max_emotion = max(emotion_counts.items(), key=lambda x: x[1])
    
    # Return corresponding emoji, default to neutral
    return emotions[max_emotion[0]][1] if max_emotion[1] > 0 else emotions['neutral'][1]

def get_message_history(channel_id: str, limit: int = 50) -> List[Dict]:
    """
    Fetch the last N messages from the database for a given channel
    Returns list of messages in API format (role, content)
    """
    try:
        db_path = 'databases/interaction_logs.db'
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get last N messages ordered by timestamp
            cursor.execute("""
                SELECT DISTINCT content, is_assistant, persona_name, timestamp
                FROM messages 
                WHERE channel_id = ?
                GROUP BY content
                ORDER BY timestamp DESC
                LIMIT ?
            """, (str(channel_id), limit))
            
            messages = []
            seen_content = set()
            
            for content, is_assistant, persona_name, timestamp in cursor.fetchall():
                # Skip if we've seen this content before
                if content in seen_content:
                    continue
                seen_content.add(content)
                
                if is_assistant:
                    # Remove model name prefix if present
                    if content.startswith('[') and ']' in content:
                        content = content[content.index(']')+1:].strip()
                    messages.append({
                        "role": "assistant",
                        "content": content
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": content
                    })
            
            # Reverse to get chronological order and limit to last N messages
            messages.reverse()
            return messages[-limit:]
            
    except Exception as e:
        logging.error(f"Failed to fetch message history: {str(e)}")
        return []

def log_interaction(user_id: Union[int, str], guild_id: Optional[Union[int, str]], 
                   persona_name: str, user_message: str, assistant_reply: str, 
                   emotion: Optional[str] = None, channel_id: Optional[Union[int, str]] = None):
    """
    Log interaction details to SQLite database
    """
    try:
        db_path = 'databases/interaction_logs.db'
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Convert all values to strings to prevent type issues
            channel_id = str(channel_id) if channel_id else None
            guild_id = str(guild_id) if guild_id else None
            user_id = str(user_id)
            persona_name = str(persona_name)
            user_message = str(user_message)
            assistant_reply = str(assistant_reply)
            emotion = str(emotion) if emotion else None
            timestamp = datetime.now().isoformat()
            
            # Log user message
            cursor.execute("""
                INSERT INTO messages (
                    channel_id, guild_id, user_id, content, 
                    is_assistant, emotion, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (channel_id, guild_id, user_id, user_message, False, None, timestamp))
            
            user_message_id = cursor.lastrowid
            
            # Log assistant reply
            cursor.execute("""
                INSERT INTO messages (
                    channel_id, guild_id, user_id, persona_name,
                    content, is_assistant, emotion, parent_message_id,
                    timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (channel_id, guild_id, user_id, persona_name,
                 assistant_reply, True, emotion, user_message_id, timestamp))
            
            conn.commit()
            logging.debug(f"Successfully logged interaction for user {user_id}")
            
    except Exception as e:
        logging.error(f"Failed to log interaction: {str(e)}")
        # Fallback to JSONL logging if database fails
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'user_id': str(user_id),
                'guild_id': str(guild_id) if guild_id else None,
                'channel_id': str(channel_id) if channel_id else None,
                'persona': str(persona_name),
                'user_message': str(user_message),
                'assistant_reply': str(assistant_reply),
                'emotion': str(emotion) if emotion else None
            }
            
            with open('interaction_logs.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e2:
            logging.error(f"Failed to log interaction to JSONL: {str(e2)}")
