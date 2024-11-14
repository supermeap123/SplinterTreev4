# 🌳 Splintertree v4

A powerful Discord bot that provides access to multiple AI language models with advanced features like shared conversation context, image processing, and dynamic prompting.

## ✨ Features

### Core Features
- **Multi-Model Support**: Access to various AI models through OpenRouter and OpenPipe
- **Direct Message Support**: Full support for private messaging with the bot, with automatic model routing
- **Web Dashboard**: Real-time statistics and activity monitoring through a web interface
  - Total message statistics
  - Active channel count
  - Daily message metrics
  - Most active model tracking
  - Recent activity feed
  - Bot status control with uptime toggle
  - Auto-refreshing interface
- **Streaming Responses**: Real-time response streaming with 1-3 sentence chunks for a more natural conversation flow
- **Shared Context Database**: SQLite-based persistent conversation history shared between all models
- **Universal Image Processing**: Automatic image description and analysis for all models, regardless of native vision support
- **File Handling**: Support for text files and images
- **Response Reroll**: Button to generate alternative responses
- **Emotion Analysis**: Reactions based on message sentiment
- **Status Updates**: Configurable status display with uptime tracking and custom messages
- **Dynamic System Prompts**: Customizable per-channel system prompts with variable support
- **Agent Cloning**: Create custom variants of existing agents with unique system prompts
- **PST Timezone Preference**: All time-related operations use Pacific Standard Time (PST) by default
- **User ID Resolution**: Automatically resolves Discord user IDs to usernames in messages
- **Default Model Configuration**: Prioritizes the default model when the bot is mentioned or specific keywords are used
- **Attachment-Only Processing**: Handles messages containing only attachments (images, text files) without additional text
- **Automatic Database Initialization**: Schema is automatically applied on bot startup
- **Improved Error Handling and Logging**: Enhanced error reporting for better troubleshooting and maintenance
- **OpenPipe Request Reporting**: Automatic logging of each message processed by context cogs to OpenPipe for analysis and potential model improvement
- **Message ID Tracking**: Prevents duplicate messages by tracking processed message IDs
- **Extended Model List**: Support for additional models and providers
- **Context Management Enhancements**: Improved context handling with commands to manage context size and history

### Special Capabilities
- **Enhanced Vision Processing**: All models can now process and respond to images, with descriptions provided for non-vision models
- **Context Management**: Per-channel message history with configurable window size
- **Cross-Model Context**: Models can see and reference each other's responses
- **File Processing**: Automatic content extraction from text files
- **Dynamic Prompting**: Customizable system prompts per channel/server
- **Model Cloning**: Ability to clone existing models with custom prompts and settings
- **Intelligent Router Mode**: Advanced message routing system that automatically directs messages to the most appropriate model based on:
  - Vision content detection and complexity analysis
  - Technical support requirements and code analysis
  - Creative writing and content generation needs
  - Conversation type (analytical, personal, multilingual)
  - Message complexity and length
  - Activate with `!activate` in any channel to enable automatic routing

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

### Testing
The project includes a comprehensive test suite covering all core functionality:

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_router_cog.py
```

Key test areas include:
- Base cog functionality (message handling, response generation)
- Router cog (message routing, model selection)
- Context management (database operations, history tracking)
- Individual model cogs (response generation, error handling)
- Management functions (administrative commands)

## ⚙️ Configuration

### Environment Variables
- `DISCORD_TOKEN`: Your Discord bot token
- `OPENROUTER_API_KEY`: OpenRouter API key
- `OPENPIPE_API_KEY`: OpenPipe API key
- `OPENPIPE_API_URL`: OpenPipe API URL
- `PORT`: Port for web dashboard (set automatically by Heroku)
- `SECRET_KEY`: Secret key for web dashboard session management

### Configuration Files
- `config.py`: Main configuration settings
- `temperatures.json`: Model temperature settings
- `dynamic_prompts.json`: Custom prompts per channel
- `databases/interaction_logs.db`: SQLite database for conversation history
- `bot_config.json`: Bot status and uptime display settings

## 🤖 Available Models

The bot supports multiple AI models through OpenRouter and OpenPipe:
- **Vision Models**: Gemini, Llama32_90b, Llama32_11b
- **Language Models**: Mixtral, Claude3Haiku, Inferor, Nemotron, Noromaid, Rplus, OpenChat, Dolphin, Gemma, Ministral, Liquid, Hermes, Goliath, Pixtral, Sonar, Sydney

Each model has specific strengths and is automatically selected based on the message content and requirements.

## 📝 Commands

See `!help` for a complete list of available commands and features.

## 🔄 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
