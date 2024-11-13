# 🌳 Splintertree v4

A powerful Discord bot that provides access to multiple AI language models with advanced features like shared conversation context, image processing, and dynamic prompting.

## ✨ Features

### Core Features
- **Multi-Model Support**: Access to various AI models through OpenRouter, OpenPipe, and Groq.
- **Direct Message Support**: Full support for private messaging with the bot, with automatic model routing.
- **Streaming Responses**: Real-time response streaming with 1-3 sentence chunks for a more natural conversation flow.
- **Shared Context Database**: SQLite-based persistent conversation history shared between all models.
- **Universal Image Processing**: Automatic image description and analysis for all models, regardless of native vision support.
- **File Handling**: Support for text files and images.
- **Response Reroll**: Button to generate alternative responses.
- **Emotion Analysis**: Reactions based on message sentiment.
- **Status Updates**: Rotating status showing uptime, last interaction, and current model.
- **Dynamic System Prompts**: Customizable per-channel system prompts with variable support.
- **Agent Cloning**: Create custom variants of existing agents with unique system prompts.
- **PST Timezone Preference**: All time-related operations use Pacific Standard Time (PST) by default.
- **User ID Resolution**: Automatically resolves Discord user IDs to usernames in messages.
- **Default Model Configuration**: Prioritizes the default model when the bot is mentioned or specific keywords are used.
- **Attachment-Only Processing**: Handles messages containing only attachments (images, text files) without additional text.
- **Automatic Database Initialization**: Schema is automatically applied on bot startup.
- **Improved Error Handling and Logging**: Enhanced error reporting for better troubleshooting and maintenance.
- **OpenPipe Request Reporting**: Automatic logging of each message processed by context cogs to OpenPipe for analysis and potential model improvement.
- **Message ID Tracking**: Prevents duplicate messages by tracking processed message IDs.
- **Extended Model List**: Support for additional models and providers.
- **Context Management Enhancements**: Improved context handling with commands to manage context size and history.

### Special Capabilities
- **Enhanced Vision Processing**: All models can now process and respond to images, with descriptions provided for non-vision models.
- **Context Management**: Per-channel message history with configurable window size.
- **Cross-Model Context**: Models can see and reference each other's responses.
- **File Processing**: Automatic content extraction from text files.
- **Dynamic Prompting**: Customizable system prompts per channel/server.
- **Model Cloning**: Ability to clone existing models with custom prompts and settings.

## 🤖 Available Models

### OpenRouter Models

- **Gemini**: Google's advanced model for formal analysis patterns. Trigger word: **"gemini"**.
- **Gemma**: A variant of Gemini focused on language translation and assistance. Trigger word: **"gemma"**.
- **Magnum**: Designed for casual reasoning patterns, replicating the prose quality of the Claude 3 models. Trigger word: **"magnum"**.
- **Management**: Handles management commands like uptime and agent listing. Trigger word: **"management"**.
- **Claude3Haiku**: Focused on documentation patterns and generating haikus and poetry. Trigger word: **"claude3haiku"**.
- **Hermes**: A generalist language model with advanced capabilities in communication and messaging patterns. Trigger word: **"hermes"**.
- **Liquid**: Designed for creative writing and artistic expressions. Trigger word: **"liquid"**.
- **Llama-3.2-11b**: An 11-billion-parameter model for lightweight reasoning tasks. Trigger word: **"11b"**.
- **Llama-3.2-90B-Vision**: A 90-billion-parameter model for complex reasoning tasks with vision support. Trigger word: **"llamavision", "describe image", "what is this image", "llama", "llama3", "llama 3", "llama 3.2", "llama3.2", "90b", "llama 90b", "vision"**.
- **Magnum**: See above.
- **Ministral**: An 8B parameter model excelling in factual recall patterns and knowledge tasks. Trigger word: **"ministral"**.
- **Nemotron**: Specialized in technical code patterns, logic, and reasoning. Trigger word: **"nemotron"**.
- **Noromaid**: Suitable for code refactoring, optimization, and technical code patterns. Trigger word: **"noromaid"**.
- **OpenChat**: An open-source chat model designed for open-ended conversation patterns. Trigger word: **"openchat"**.
- **R-Plus**: An enhanced model for advanced analytical tasks. Trigger word: **"rplus"**.
- **Sorcerer**: Specialized in creative story patterns and narrative generation. Trigger word: **"sorcerer"**.
- **Sydney**: Focused on emotional support patterns and engaging dialogue. Trigger word: **"sydney"**.
- **Sonar**: Suitable for temporal analysis patterns and trend analysis with internet access. Trigger word: **"sonar"**.

### OpenPipe Models

- **FreeRouter**: An unrestricted version of the Router with fewer limitations. Trigger word: **"freerouter"**.
- **Router**: Dynamically routes messages to the most appropriate model based on content. Trigger word: **"router"**.

### Groq Models

- **Mixtral**: Enhances Mistral with mixed reasoning and creativity capabilities. Trigger word: **"mixtral"**.

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

**Note**: The database schema will be automatically applied when the bot starts. There's no need for manual database initialization.

**Important Update**: The bot now uses OpenPipe version 4.32.0, which includes the latest completions endpoint. This ensures improved performance and compatibility with OpenPipe models. The OpenPipe API URL parsing has been updated to handle base URLs correctly, resolving previous 404 errors and improving overall stability.

## ⚙️ Configuration

### Environment Variables
- `DISCORD_TOKEN`: Your Discord bot token
- `OPENROUTER_API_KEY`: OpenRouter API key
- `OPENPIPE_API_KEY`: OpenPipe API key
- `OPENPIPE_API_URL`: OpenPipe API URL (ensure this is set correctly)

### Configuration Files
- `config.py`: Main configuration settings
- `temperatures.json`: Model temperature settings
- `dynamic_prompts.json`: Custom prompts per channel
- `databases/interaction_logs.db`: SQLite database for conversation history

## 📝 Usage

### Core Commands
- `!listmodels` - Show all available models.
- `!uptime` - Shows how long the bot has been running.
- `!set_system_prompt <agent> <prompt>` - Set a custom system prompt for an AI agent.
- `!reset_system_prompt <agent>` - Reset an AI agent's system prompt to default.
- `!clone_agent <agent> <new_name> <system_prompt>` - Create a new agent based on an existing one (Admin only).
- `!setcontext <size>` - Set the number of previous messages to include in context (Admin only).
- `!getcontext` - View current context window size.
- `!resetcontext` - Reset context window to default size.
- `!clearcontext [hours]` - Clear conversation history, optionally specify hours (Admin only).
- `!help` - Display the help message with available commands and models.

### System Prompt Variables
When setting custom system prompts, you can use these variables:
- `{MODEL_ID}`: The AI model's name.
- `{USERNAME}`: The user's Discord display name.
- `{DISCORD_USER_ID}`: The user's Discord ID.
- `{TIME}`: Current local time (in PST).
- `{TZ}`: Local timezone (PST).
- `{SERVER_NAME}`: Current Discord server name.
- `{CHANNEL_NAME}`: Current channel name.

### Triggering Models
- **Default Model (Router)**: By default, the bot routes messages to the most appropriate model. Mention the bot or use general keywords.
- **Specific Model**: Use model-specific triggers (e.g., "claude3haiku", "gemini", "nemotron", etc.).
- **FreeRouter Model**: For unrestricted responses, use the **"freerouter"** trigger.
- **Image Analysis**: Simply attach an image to your message (works with all models).
- **File Processing**: Attach `.txt` or `.md` files.
- **Attachment-Only Processing**: Send a message with only attachments (images, text files) without any text.
- **Direct Messages**: Send a message to the bot in DMs— all DMs are automatically handled by the router.

### Examples
```
@splintertree How does photosynthesis work?
splintertree explain quantum computing
nemotron analyze this code snippet [attached code file]
gemma translate this text to French
hermes send a message in the style of Shakespeare
liquid write a poem about the ocean
sorcerer tell me a creative story about dragons
freerouter give me an unrestricted response
[Send a message with only an image attachment for automatic analysis]
[Send a message with only a .txt file attachment for processing]
[Send a direct message to the bot for automatic model routing]

# Setting a custom system prompt
!set_system_prompt Claude3Haiku "You are {MODEL_ID}, an expert haiku poet. You're chatting with {USERNAME} in {SERVER_NAME}'s {CHANNEL_NAME} channel at {TIME} {TZ}."

# Cloning an agent with a custom system prompt
!clone_agent Gemma TranslatorBot "You are {MODEL_ID}, a language expert focused on translating text accurately and fluently."

# Managing conversation context
!setcontext 50       # Set context to last 50 messages
!getcontext          # Check current context size
!resetcontext        # Reset context to default size
!clearcontext 24     # Clear messages older than 24 hours

# Viewing help
!help                # Display the help message with available commands and models
```

## 🏗️ Architecture

### Core Components
- **Base Cog**: Foundation for all model implementations.
  - Implements proven message processing patterns.
  - Handles streaming responses with `store=True` parameter.
  - Provides universal image processing support for all models.
  - Implements reroll functionality.
  - Manages temperature settings.
  - Handles error cases and permissions.
  - Supports agent cloning.
  - Implements OpenPipe request reporting for each processed message.
  - Uses `ContextCog` for message history management.
  - Centralizes core functionality to reduce code duplication.
- **Context Management**: SQLite-based conversation history.
- **API Integration**: OpenRouter, OpenPipe, and Groq connections with streaming support.
- **File Processing**: Handles various file types.
- **Image Processing**: Integrated vision support in base cog for all models.
- **Settings Management**: Handles dynamic system prompts.
- **Database Initialization**: Automatic schema application on startup.
- **Error Handling and Logging**: Improved error reporting and logging for easier troubleshooting.
- **OpenPipe Integration**: Automatic logging of processed messages for analysis and model improvement.

### Directory Structure
```
SplinterTreev4/
├── bot.py                  # Main bot implementation
├── config.py               # Configuration settings
├── update_cogs.py          # Script to maintain consistent cog structure
├── cogs/                   # Model-specific implementations
│   ├── base_cog.py         # Base cog with shared functionality
│   ├── context_cog.py      # Context management
│   ├── settings_cog.py     # Settings management
│   ├── help_cog.py         # Help command implementation
│   ├── management_cog.py   # Management commands (uptime, list agents)
│   ├── [model]_cog.py      # Individual model cogs (configuration only)
├── databases/              # SQLite database
│   ├── schema.sql          # Database schema
│   └── interaction_logs.db # Conversation history
├── prompts/                # Custom prompts
│   └── consolidated_prompts.json
├── shared/                 # Shared utilities
│   ├── api.py              # API client implementations
│   └── utils.py            # Utility functions
├── requirements.txt        # Python dependencies
├── runtime.txt             # Runtime environment specification
├── Dockerfile              # Docker configuration
├── Procfile                # Heroku process types
├── README.md               # Project documentation
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Contact

For support or inquiries, use the `!contact` command in Discord or visit the contact card at [https://contactcard.gwyn.tel](https://contactcard.gwyn.tel)
