# shared/utils.py

import json
import logging
from datetime import datetime

def analyze_emotion(text):
    """
    Analyze the emotional content of text using simple keyword matching.
    Returns Discord-compatible emoji
    """
    # Define emotion keywords and corresponding Discord emojis
    emotions = {
        'joy': (['happy', 'joy', 'excited', 'great', 'wonderful', 'love', 'glad'], '😄'),
        'sadness': (['sad', 'sorry', 'unfortunate', 'regret', 'miss', 'lonely'], '😢'),
        'anger': (['angry', 'mad', 'furious', 'annoyed', 'frustrated'], '😠'),
        'fear': (['afraid', 'scared', 'worried', 'nervous', 'anxious'], '😨'),
        'surprise': (['wow', 'amazing', 'incredible', 'unexpected', 'surprised'], '😮'),
        'neutral': (['ok', 'fine', 'alright', 'neutral'], '👍')
    }
    
    # Convert text to lowercase for matching
    text = text.lower()
    
    # Count emotion keywords
    emotion_counts = {emotion: 0 for emotion in emotions}
    for emotion, (keywords, _) in emotions.items():
        for keyword in keywords:
            emotion_counts[emotion] += text.count(keyword)
    
    # Find emotion with highest count
    max_emotion = max(emotion_counts.items(), key=lambda x: x[1])
    
    # Return corresponding emoji, default to neutral
    return emotions[max_emotion[0]][1] if max_emotion[1] > 0 else emotions['neutral'][1]

def log_interaction(user_id, guild_id, persona_name, user_message, assistant_reply, emotion):
    """
    Log interaction details to a JSONL file for analysis
    """
    try:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': str(user_id),
            'guild_id': str(guild_id) if guild_id else None,
            'persona': persona_name,
            'user_message': user_message,
            'assistant_reply': assistant_reply,
            'emotion': emotion
        }
        
        with open('interaction_logs.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
            
    except Exception as e:
        logging.error(f"Failed to log interaction: {str(e)}")
