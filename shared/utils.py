import json
import logging
import sqlite3
from datetime import datetime
from typing import Optional

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

def log_interaction(user_id: str, guild_id: Optional[str], persona_name: str, 
                   user_message: str, assistant_reply: str, emotion: Optional[str] = None,
                   channel_id: Optional[str] = None):
    """
    Log interaction details to SQLite database
    """
    try:
        db_path = 'databases/interaction_logs.db'
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Log user message
            cursor.execute("""
                INSERT INTO messages (
                    channel_id, guild_id, user_id, content, 
                    is_assistant, emotion
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (channel_id, guild_id, user_id, user_message, False, None))
            
            user_message_id = cursor.lastrowid
            
            # Log assistant reply
            cursor.execute("""
                INSERT INTO messages (
                    channel_id, guild_id, user_id, persona_name,
                    content, is_assistant, emotion, parent_message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (channel_id, guild_id, user_id, persona_name,
                 assistant_reply, True, emotion, user_message_id))
            
            conn.commit()
            
    except Exception as e:
        logging.error(f"Failed to log interaction: {str(e)}")
        # Fallback to JSONL logging if database fails
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'user_id': str(user_id),
                'guild_id': str(guild_id) if guild_id else None,
                'channel_id': str(channel_id) if channel_id else None,
                'persona': persona_name,
                'user_message': user_message,
                'assistant_reply': assistant_reply,
                'emotion': emotion
            }
            
            with open('interaction_logs.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e2:
            logging.error(f"Failed to log interaction to JSONL: {str(e2)}")
