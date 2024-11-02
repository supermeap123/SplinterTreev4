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
- **Concise Summarization**: Llama 3.2 3B model provides clear, concise summaries and responses in 3 sentences or less

### Special Capabilities
- **Enhanced Vision Processing**: All models can now process and respond to images, with descriptions provided for non-vision models
- **Context Management**: Per-channel message history with configurable window size
- **Cross-Model Context**: Models can see and reference each other's responses
- **File Processing**: Automatic content extraction from text files
- **Dynamic Prompting**: Customizable system prompts per channel/server
- **Response Filtering**: Llama 3.2 3B model helps filter and refine responses for clarity and appropriateness

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
- **Llama 3.2 3B**: Efficient model focused on concise summarization and response filtering
- **NoroMaid-20B**: Advanced conversational model
- **MythoMax-L2-13B**: Versatile language model
- **Grok**: xAI's latest conversational model
- **Hermes**: Specialized, less restrictive conversation model
- **Sonar**: Enhanced context understanding
- **Liquid**: Optimized for specific tasks
- **O1-Mini**: Lightweight, efficient model
- **MOA**: Mixture of Agents model based on GPT4o

[Rest of README content remains unchanged...]
