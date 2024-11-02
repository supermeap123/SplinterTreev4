CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY,
    channel_id TEXT NOT NULL UNIQUE,
    guild_id TEXT NOT NULL,
    last_message_id TEXT,
    last_response_id TEXT,
    last_human TEXT,
    last_assistant TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS guilds (
    id INTEGER PRIMARY KEY,
    guild_id TEXT NOT NULL UNIQUE,
    active_model TEXT NOT NULL DEFAULT 'sydney',
    temperature REAL NOT NULL DEFAULT 0.7,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    message_id TEXT NOT NULL UNIQUE,
    channel_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deactivated_channels (
    id INTEGER PRIMARY KEY,
    channel_id TEXT NOT NULL UNIQUE,
    guild_id TEXT NOT NULL,
    deactivated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_channels_channel_id ON channels(channel_id);
CREATE INDEX IF NOT EXISTS idx_channels_guild_id ON channels(guild_id);
CREATE INDEX IF NOT EXISTS idx_guilds_guild_id ON guilds(guild_id);
CREATE INDEX IF NOT EXISTS idx_messages_message_id ON messages(message_id);
CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON messages(channel_id);
CREATE INDEX IF NOT EXISTS idx_messages_guild_id ON messages(guild_id);
CREATE INDEX IF NOT EXISTS idx_deactivated_channels_channel_id ON deactivated_channels(channel_id);
CREATE INDEX IF NOT EXISTS idx_deactivated_channels_guild_id ON deactivated_channels(guild_id);
