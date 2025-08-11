# Neurocord

Your server’s smart sidekick for finding stuff fast and watching together. ⚡️🔍🎬

## What it does

- **AI-powered knowledge base**: Save messages and search them later by meaning, not just keywords.
- **Watch Together**: Spin up a Watch2Gether room right from Discord and share the link with your server.

## Commands (slash)

- `/save content:<text>` — Save content with an AI embedding for semantic search
- `/search query:<terms> [limit:1-10]` — Find the most relevant saved content
- `/delete content_id:<uuid>` — Delete content you created
- `/edit content_id:<uuid> new_content:<text>` — Update content and its embedding
- `/my_content` — View your saved items
- `/watch [url:<video_url>]` — Create or fetch your server’s Watch2Gether room (24h)
- `/watch-delete` — Remove the saved room entry from the bot
- `/help` — See all commands and examples

## Tech stack

- **Discord**: nextcord
- **Embeddings**: OpenAI
- **Database**: Supabase (PostgreSQL + pgvector in the DB)
- **Runtime/Tooling**: Python 3.13, uv, Ruff, Pytest

## Quick start

### Prerequisites
- Python 3.13+
- Discord bot token
- Supabase project (URL + service key)
- OpenAI API key

### Install
```bash
git clone https://github.com/sxnfer/neurocord.git
cd neurocord
uv sync
```

### Configure
Create a `.env` with:
```
DISCORD_TOKEN=your_discord_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_api_key
WATCH2GETHER_API_KEY=your_watch2gether_api_key  # optional, required for /watch

# Optional tweaks
COMMAND_PREFIX=!
MAX_SEARCH_RESULTS=10
LOGGING_PRESET=development  # development | production | minimal
```

### Run
```bash
uv run python main.py
```

## Development

```bash
# Install deps
uv sync

# Add a dep
uv add <package>

# Test
uv run pytest

# Lint & format
uv run ruff check .
uv run ruff format
```

## Contributing

Got ideas? PRs welcome!
1. Fork the repo
2. Create a feature branch
3. Make changes + tests
4. Run linting and tests
5. Open a PR

## Need help?

Open an issue and we’ll take it from there. 💬