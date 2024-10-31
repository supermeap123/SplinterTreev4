# 🌳 Splintertree v4

A powerful Discord bot that provides access to multiple AI language models with advanced features like shared conversation context, image processing, and dynamic prompting.

## ✨ Features

### Core Features
- **Multi-Model Support**: Access to various AI models through OpenRouter and OpenPipe
- **Streaming Responses**: Real-time response streaming with 1-3 sentence chunks for a more natural conversation flow
- **Shared Context Database**: SQLite-based persistent conversation history shared between all models
- **Image Processing**: Automatic image description and analysis
- **File Handling**: Support for text files and images
- **Response Reroll**: Button to generate alternative responses
- **Emotion Analysis**: Reactions based on message sentiment
- **Status Updates**: Rotating status showing uptime, last interaction, and current model
- **Dynamic System Prompts**: Customizable per-channel system prompts with variable support
- **Agent Cloning**: Create custom variants of existing agents with unique system prompts
- **PST Timezone Preference**: All time-related operations use Pacific Standard Time (PST) by default
- **User ID Resolution**: Automatically resolves Discord user IDs to usernames in messages
- **Claude-2 Default**: Prioritizes Claude-2 model when the bot is mentioned or "splintertree" keyword is used
- **Attachment-Only Processing**: Handles messages containing only attachments (images, text files) without additional text
- **Automatic Database Initialization**: Schema is automatically applied on bot startup

### Special Capabilities
- **Vision Processing**: Direct image analysis with compatible models
- **Context Management**: Per-channel message history with configurable window size
- **Cross-Model Context**: Models can see and reference each other's responses
- **File Processing**: Automatic content extraction from text files
- **Dynamic Prompting**: Customizable system prompts per channel/server

## 🤖 Available Models

### OpenRouter Models
- **Claude-3 Opus**: State-of-the-art model with exceptional capabilities
- **Claude-3 Sonnet**: Balanced performance and efficiency
- **Claude-2**: Reliable general-purpose model
- **Claude-1.1**: Legacy model for specific use cases
- **Magnum**: High-performance 72B parameter model
- **Gemini Pro**: Google's advanced model
- **Mistral**: Efficient open-source model
- **Llama-2**: Open-source model with vision capabilities
- **NoroMaid-20B**: Advanced conversational model
- **MythoMax-L2-13B**: Versatile language model
- **Grok**: xAI's latest conversational model

### OpenPipe Models
- **Hermes**: Specialized conversation model
- **Sonar**: Enhanced context understanding
- **Liquid**: Optimized for specific tasks
- **O1-Mini**: Lightweight, efficient model

## 🛠️ Setup

### Prerequisites
- Python 3.10+
- Discord Bot Token
- OpenRouter API Key
- OpenPipe API Key
- SQLite3

### Installation
1. Clone the repository:
```bash
git clone https://github.com/yourusername/SplinterTreev4.git
cd SplinterTreev4
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
- Copy `.env.example` to `.env`
- Add your API keys and configuration

4. Run the bot:
```bash
python bot.py
```

Note: The database schema will be automatically applied when the bot starts. There's no need for manual database initialization.

**Important Update**: The bot now uses the latest OpenPipe completions endpoint, ensuring improved performance and compatibility with OpenPipe models.

## ⚙️ Configuration

### Environment Variables
- `DISCORD_TOKEN`: Your Discord bot token
- `OPENROUTER_API_KEY`: OpenRouter API key
- `OPENPIPE_API_KEY`: OpenPipe API key

### Configuration Files
- `config.py`: Main configuration settings
- `temperatures.json`: Model temperature settings
- `dynamic_prompts.json`: Custom prompts per channel
- `databases/interaction_logs.db`: SQLite database for conversation history

## 📝 Usage

### Core Commands
- `!listmodels` - Show all available models
- `!set_system_prompt <agent> <prompt>` - Set a custom system prompt for an AI agent
- `!reset_system_prompt <agent>` - Reset an AI agent's system prompt to default
- `!clone_agent <agent> <new_name> <system_prompt>` - Create a new agent based on an existing one (Admin only)

### Context Management Commands
- `!setcontext <size>` - Set the number of previous messages to include in context (Admin only)
- `!getcontext` - View current context window size
- `!resetcontext` - Reset context window to default size (Admin only)
- `!clearcontext [hours]` - Clear conversation history, optionally specify hours (Admin only)

### System Prompt Variables
When setting custom system prompts, you can use these variables:
- `{MODEL_ID}`: The AI model's name
- `{USERNAME}`: The user's Discord display name
- `{DISCORD_USER_ID}`: The user's Discord ID
- `{TIME}`: Current local time (in PST)
- `{TZ}`: Local timezone (PST)
- `{SERVER_NAME}`: Current Discord server name
- `{CHANNEL_NAME}`: Current channel name

### Triggering Models
- **Default Model (Claude-2)**: Mention the bot or use "splintertree" keyword
- **Specific Model**: Use model-specific triggers (e.g., "claude", "gemini", "grok", etc.)
- **Image Analysis**: Simply attach an image to your message
- **File Processing**: Attach .txt or .md files
- **Attachment-Only Processing**: Send a message with only attachments (images, text files) without any text

### Examples
```
@Splintertree How does photosynthesis work?
splintertree explain quantum computing
claude what is the meaning of life?
gemini analyze this image [attached image]
grok tell me a joke
[Send a message with only an image attachment for automatic analysis]
[Send a message with only a .txt file attachment for automatic processing]

# Setting a custom system prompt
!set_system_prompt Claude-3 "You are {MODEL_ID}, an expert in science communication. You're chatting with {USERNAME} in {SERVER_NAME}'s {CHANNEL_NAME} channel at {TIME} {TZ}."

# Cloning an agent with a custom system prompt
!clone_agent Claude-3 ScienceGPT "You are {MODEL_ID}, a science expert focused on explaining complex concepts in simple terms. You always use analogies and real-world examples in your explanations."

# Managing conversation context
!setcontext 50  # Set context to last 50 messages
!getcontext     # Check current context size
!clearcontext 24  # Clear messages older than 24 hours
```

## 🏗️ Architecture

### Core Components
- **Base Cog**: Foundation for all model implementations
  - Handles message processing
  - Manages streaming responses
  - Provides vision support for compatible models
  - Implements reroll functionality
  - Manages temperature settings
  - Handles error cases and permissions
  - Supports agent cloning
- **Context Management**: SQLite-based conversation history
- **API Integration**: OpenRouter and OpenPipe connections with streaming support
- **File Processing**: Handles various file types
- **Image Processing**: Integrated vision support in base cog
- **Settings Management**: Handles dynamic system prompts
- **Database Initialization**: Automatic schema application on startup

### Directory Structure
```
SplinterTreev4/
├── bot.py              # Main bot implementation
├── config.py           # Configuration settings
├── cogs/               # Model-specific implementations
│   ├── base_cog.py    # Base cog with shared functionality
│   │   ├── Message Processing
│   │   ├── Vision Support
│   │   ├── Streaming
│   │   └── Error Handling
│   ├── context_cog.py # Context management
│   ├── settings_cog.py # Settings management
│   └── [model]_cog.py # Individual model cogs
├── databases/          # SQLite database
│   ├── schema.sql     # Database schema
│   └── interaction_logs.db # Conversation history
└── shared/            # Shared utilities
    ├── api.py        # API client implementations
    └── utils.py      # Utility functions
```

## 🔧 Development

### Adding New Models
1. Create a new cog file in `cogs/`
2. Inherit from `BaseCog`
3. Configure model-specific settings:
   ```python
   class NewModelCog(BaseCog):
       def __init__(self, bot):
           super().__init__(
               bot=bot,
               name="Model-Name",
               nickname="Nickname",
               trigger_words=['trigger1', 'trigger2'],
               model="provider/model-id",
               provider="openrouter",  # or "openpipe"
               prompt_file="prompt_name",
               supports_vision=False  # or True for vision-capable models
           )
   ```
4. The base cog provides all core functionality including:
   - Message processing
   - Vision support (if enabled)
   - Streaming responses
   - Error handling
   - Temperature management
   - Context integration
   - Agent cloning

### Custom Prompts
Channel-specific prompts are stored in `dynamic_prompts.json`:
```json
{
  "guild_id": {
    "channel_id": "Custom system prompt with {MODEL_ID} and other variables"
  }
}
```

### Database Schema
The SQLite database includes tables for:
- `messages`: Stores all conversation messages
- `context_windows`: Stores per-channel context settings
- `logs`: Stores interaction logs for API calls

The schema is automatically applied when the bot starts, ensuring the database is always up-to-date.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Contact

For support or inquiries, use the `!contact` command in Discord or visit the contact card at https://sydney.gwyn.tel/contactcard
