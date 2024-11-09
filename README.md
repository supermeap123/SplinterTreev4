# 🌳 Splintertree v4

A powerful Discord bot that provides access to multiple AI language models with advanced features like shared conversation context, image processing, and dynamic prompting.

## ✨ Features

### Core Features
- **Multi-Model Support**: Access to various AI models through OpenRouter and OpenPipe
- **Streaming Responses**: Real-time response streaming with 1-3 sentence chunks for a more natural conversation flow
- **Shared Context Database**: SQLite-based persistent conversation history shared between all models
- **Universal Image Processing**: Automatic image description and analysis for all models, regardless of native vision support
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
- **Improved Error Handling and Logging**: Enhanced error reporting for better troubleshooting and maintenance
- **OpenPipe Request Reporting**: Automatic logging of each message processed by context cogs to OpenPipe for analysis and potential model improvement
- **Message ID Tracking**: Prevents duplicate messages by tracking processed message IDs.

### Special Capabilities
- **Enhanced Vision Processing**: All models can now process and respond to images, with descriptions provided for non-vision models
- **Context Management**: Per-channel message history with configurable window size
- **Cross-Model Context**: Models can see and reference each other's responses
- **File Processing**: Automatic content extraction from text files
- **Dynamic Prompting**: Customizable system prompts per channel/server

## 🤖 Available Models

### OpenRouter Models
- **Magnum**: A series of models designed to replicate the prose quality of the Claude 3 models, specifically Sonnet(https://openrouter.ai/anthropic/claude-3.5-sonnet) and Opus(https://openrouter.ai/anthropic/claude-3-opus). The model is fine-tuned on top of Qwen2.5 72B. Trigger word: "magnum". Note: Sometimes Magnum thinks it's from Anthropic but it's really from anthracite-org.
- **Gemini Pro**: Google's advanced model.
- **Mistral**: Ministral 8B is an 8B parameter model featuring a unique interleaved sliding-window attention pattern for faster, memory-efficient inference. Designed for edge use cases, it supports up to 128k context length and excels in knowledge and reasoning tasks. It outperforms peers in the sub-10B category, making it perfect for low-latency, privacy-first applications.
- **Llama-2**: The Llama 90B Vision model is a top-tier, 90-billion-parameter multimodal model designed for the most challenging visual reasoning and language tasks. It offers unparalleled accuracy in image captioning, visual question answering, and advanced image-text comprehension. Pre-trained on vast multimodal datasets and fine-tuned with human feedback, the Llama 90B Vision is engineered to handle the most demanding image-based AI tasks. This model is perfect for industries requiring cutting-edge multimodal AI capabilities, particularly those dealing with complex, real-time visual and textual analysis. Usage of this model is subject to Meta's Acceptable Use Policy.
- **NoroMaid-20B**: A collab between IkariDev and Undi. This merge is suitable for RP, ERP, and general knowledge.
- **MythoMax-L2-13B**: One of the highest performing and most popular fine-tunes of Llama 2 13B, with rich descriptions and roleplay.
- **Grok**: Terrible bot from xai. It thinks it's from Hitchhikers Guide to the Galaxy.

### OpenPipe Models
- **Hermes**: Hermes 3 is a generalist language model with many improvements over Hermes 2, including advanced agentic capabilities, much better roleplaying, reasoning, multi-turn conversation, long context coherence, and improvements across the board. Hermes 3 405B is a frontier-level, full-parameter finetune of the Llama-3.1 405B foundation model, focused on aligning LLMs to the user, with powerful steering capabilities and control given to the end user. The Hermes 3 series builds and expands on the Hermes 2 set of capabilities, including more powerful and reliable function calling and structured output capabilities, generalist assistant capabilities, and improved code generation skills. Hermes 3 is competitive, if not superior, to Llama-3.1 Instruct models at general capabilities, with varying strengths and weaknesses attributable between the two.
- **Sonar**: Llama 3.1 Sonar is Perplexity's latest model family. It surpasses their earlier Sonar models in cost-efficiency, speed, and performance. The model is built upon the Llama 3.1 405B and has internet access.
- **Liquid**: Liquid's 40.3B Mixture of Experts (MoE) model. Liquid Foundation Models (LFMs) are large neural networks built with computational units rooted in dynamic systems. LFMs are general-purpose AI models that can be used to model any kind of sequential data, including video, audio, text, time series, and signals.
- **O1-Mini**: The latest and strongest model family from OpenAI, o1 is designed to spend more time thinking before responding. The o1 models are optimized for math, science, programming, and other STEM-related tasks. They consistently exhibit PhD-level accuracy on benchmarks in physics, chemistry, and biology. Note: This model is currently experimental and not suitable for production use-cases, and may be heavily rate-limited.
- **MOA**: The latest and strongest model family from OpenPipe, moa is designed to spend more time thinking before responding.

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
- `!listmodels` - Show all available models
- `!uptime` - Shows how long the bot has been running
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
- **Image Analysis**: Simply attach an image to your message (works with all models)
- **File Processing**: Attach .txt or .md files
- **Attachment-Only Processing**: Send a message with only attachments (images, text files) without any text

### Examples
```
@Splintertree How does photosynthesis work?
splintertree explain quantum computing
claude what is the meaning of life?
gemini analyze this image [attached image]
grok tell me a joke
[Send a message with only an image attachment for automatic analysis with any model]
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
  - Implements Sydney's proven message processing pattern
  - Handles streaming responses with store=True parameter
  - Provides universal image processing support for all models
  - Implements reroll functionality
  - Manages temperature settings
  - Handles error cases and permissions
  - Supports agent cloning
  - Implements OpenPipe request reporting for each processed message
  - Uses context_cog for message history management
  - Centralizes core functionality to reduce code duplication
- **Context Management**: SQLite-based conversation history
- **API Integration**: OpenRouter and OpenPipe connections with streaming support
- **File Processing**: Handles various file types
- **Image Processing**: Integrated vision support in base cog for all models
- **Settings Management**: Handles dynamic system prompts
- **Database Initialization**: Automatic schema application on startup
- **Error Handling and Logging**: Improved error reporting and logging for easier troubleshooting
- **OpenPipe Integration**: Automatic logging of processed messages for analysis and model improvement

### Directory Structure
```
SplinterTreev4/
├── bot.py              # Main bot implementation
├── config.py           # Configuration settings
├── update_cogs.py      # Script to maintain consistent cog structure
├── cogs/               # Model-specific implementations
│   ├── base_cog.py    # Base cog with shared functionality
│   │   ├── Message Processing (Sydney's pattern)
│   │   ├── Vision Support
│   │   ├── Streaming with store=True
│   │   ├── Error Handling
│   │   └── OpenPipe Reporting
│   ├── context_cog.py # Context management
│   ├── settings_cog.py # Settings management
│   └── [model]_cog.py # Individual model cogs (configuration only)
├── databases/          # SQLite database
│   ├── schema.sql     # Database schema
│   └── interaction_logs.db # Conversation history
└── shared/            # Shared utilities
    ├── api.py        # API client implementations
    └── utils.py      # Utility functions
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Contact

For support or inquiries, use the `!contact` command in Discord or visit the contact card at https://sydney.gwyn.tel/contactcard
