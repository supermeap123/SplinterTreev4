# Discord AI Bot

A Discord bot that provides access to various AI models through simple commands and mentions.

## Features

- Multiple AI model support including Sydney, Claude, Gemini, GPT-4, and more
- Adjustable response creativity via temperature setting
- Conversation context management
- Channel-specific activation controls
- Web interface for monitoring (optional)

## Commands

- **@Bot [message]** - Start a conversation with the bot by mentioning it
- **/model [model_name]** - Change the AI model
- **/temperature [0.0-2.0]** - Adjust response creativity
- **/context clear** - Clear conversation history
- **/context show** - Display current conversation history
- **/activate** - Enable bot message processing in the current channel
- **/deactivate** - Disable bot message processing in the current channel
- **/help** - Show available commands and features

## Available Models

- sydney (default)
- claude2
- claude3opus
- claude3sonnet
- gemini
- geminipro
- gemma
- grok
- hermes
- liquid
- llama32_3b
- llama32_11b
- magnum
- ministral
- moa
- mythomax
- nemotron
- noromaid
- o1mini
- openchat
- rplus
- sonar

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your credentials
4. Run the bot: `python bot.py`

### Environment Variables

Required variables in `.env`:

```
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
```

## Optional Web Interface

To run the web interface:

1. Set additional environment variables in `.env`:
```
WEB_USERNAME=your_username
WEB_PASSWORD=your_password
```

2. Run the web server: `python run_web.py`

## Permissions

The bot requires the following permissions:
- Read Messages/View Channels
- Send Messages
- Send Messages in Threads
- Embed Links
- Attach Files
- Read Message History
- Add Reactions

Channel management commands (/activate, /deactivate) require users to have either:
- Manage Channels permission
- Manage Messages permission

## Development

- Written in Python using discord.py
- Uses SQLite for data storage
- Follows Discord API best practices
- Includes error handling and rate limiting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
