CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    guild_id TEXT,
    user_id TEXT NOT NULL,
    persona_name TEXT,
    content TEXT NOT NULL,
    is_assistant BOOLEAN NOT NULL,
    emotion TEXT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_summaries (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    start_timestamp TEXT NOT NULL,
    end_timestamp TEXT NOT NULL,
    summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS context_windows (
    channel_id TEXT PRIMARY KEY,
    window_size INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS deactivated_channels (
    channel_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    PRIMARY KEY (channel_id, guild_id)
);

-- Add the channels table
CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    last_message_id TEXT,
    last_response_id TEXT,
    last_human TEXT,
    last_assistant TEXT,
    last_updated TEXT,
    PRIMARY KEY (channel_id, guild_id)
);
