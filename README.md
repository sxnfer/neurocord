# Discord Bot

A powerful Discord bot designed to enhance server functionality through intelligent content management and collaborative entertainment features.

## Overview

This Discord bot transforms how communities interact within their servers by providing two core capabilities:

1. **Intelligent Content Management** - Enables semantic search and organization of server content, allowing members to save, search, and retrieve information using natural language queries
2. **Collaborative Entertainment** - Facilitates shared viewing experiences through integrated Watch2gether functionality

## How It Enhances Your Server

### Smart Knowledge Base
- Turn your Discord server into a searchable knowledge repository
- Members can save important information, tips, resources, and discussions
- Find relevant content using natural language searches instead of scrolling through endless message history
- Perfect for communities, study groups, gaming guilds, and professional teams

### Shared Entertainment
- Create instant watch parties for your community
- Stream videos together with synchronized playback
- Strengthen community bonds through shared viewing experiences
- Ideal for movie nights, educational content, or casual hangouts

## Technology Stack

Built with modern technologies for reliability and performance:

- **Discord Integration**: nextcord library for robust Discord API interaction
- **Semantic Search**: Vector embeddings with OpenAI for intelligent content matching
- **Database**: Supabase (PostgreSQL) with pgvector extension for efficient similarity searches
- **Python**: Version 3.13 with uv package management

## Quick Start

### Prerequisites
- Python 3.13 or higher
- Discord Developer Application and Bot Token
- Supabase account and database
- OpenAI API key (for embeddings)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd discord-bot
```

2. Install dependencies:
```bash
uv sync
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

4. Run the bot:
```bash
uv run python main.py
```

## Configuration

Create a `.env` file with the following variables:
```
DISCORD_TOKEN=your_discord_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_api_key
WATCH2GETHER_API_KEY=your_watch2gether_api_key # optional, required for /watch
```

## Development

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>

# Run tests
uv run pytest

# Format code
uv run ruff format

# Lint code
uv run ruff check .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Support

For questions, issues, or feature requests, please [create an issue](link-to-issues) on GitHub.