"""Discord bot main entry point."""

import asyncio
import logging
from pathlib import Path

import nextcord
from nextcord.ext import commands

from utils.config import get_config


def setup_logging() -> None:
    """Configure logging for the bot."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
    )


class DiscordBot(commands.Bot):
    """Main Discord bot class with async initialization."""

    def __init__(self):
        # Initialize the bot with required intents
        intents = nextcord.Intents.default()
        intents.message_content = True  # Required for message commands

        super().__init__(
            command_prefix="!",  # Fallback for text commands
            intents=intents,
            help_command=None,  # We'll create our own
        )

    async def on_ready(self):
        """Called when bot successfully connects to Discord."""
        print(f"🤖 {self.user} has connected to Discord!")
        print(f"📊 Bot is in {len(self.guilds)} servers")

        # Sync slash commands globally (takes up to 1 hour)
        try:
            await self.sync_all_application_commands()
            print("✅ Slash commands synced successfully")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

    async def load_cogs(self):
        """Load all cog modules."""
        cogs_dir = Path("cogs")

        if not cogs_dir.exists():
            print("⚠️  No cogs directory found, creating it...")
            cogs_dir.mkdir()
            return

        # Load all Python files in cogs directory
        for cog_file in cogs_dir.glob("*.py"):
            if cog_file.name.startswith("_"):
                continue  # Skip __init__.py and private files

            cog_name = f"cogs.{cog_file.stem}"
            try:
                self.load_extension(cog_name)
                print(f"✅ Loaded cog: {cog_name}")
            except Exception as e:
                print(f"❌ Failed to load cog {cog_name}: {e}")


async def main():
    """Main async entry point."""
    # Setup logging
    setup_logging()

    # Load configuration
    try:
        config = get_config()
        print("✅ Configuration loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return

    # Create and setup bot
    bot = DiscordBot()

    # Load all cogs
    await bot.load_cogs()

    # Start the bot
    try:
        print("🚀 Starting bot...")
        await bot.start(config.discord_token)
    except KeyboardInterrupt:
        print("👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
