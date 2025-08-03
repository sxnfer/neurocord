"""Discord bot main entry point."""

import asyncio
from pathlib import Path
from typing import Optional

import nextcord
from nextcord.ext import commands

from utils.config import get_config
from utils.logging_config import setup_logging_preset, get_logger, log_performance
from utils.database import db_manager


class DiscordBot(commands.Bot):
    """Main Discord bot class with async initialization."""

    def __init__(self):
        self.logger = get_logger("DiscordBot")
        self.startup_time: Optional[float] = None

        # Initialize the bot with required intents
        intents = nextcord.Intents.default()
        intents.message_content = True  # Required for message commands

        super().__init__(
            command_prefix="!",  # Fallback for text commands
            intents=intents,
            help_command=None,  # Disable default help command
        )

        self.logger.info("Bot instance created with required intents")

    async def on_ready(self):
        """Called when bot successfully connects to Discord."""
        import time

        if self.startup_time:
            total_startup = time.time() - self.startup_time
            log_performance("bot_startup", total_startup, guilds=len(self.guilds))

        self.logger.info(f"🤖 {self.user} successfully connected to Discord!")
        self.logger.info(f"📊 Active in {len(self.guilds)} servers")

        # List all registered commands before syncing
        all_commands = self.get_all_application_commands()
        self.logger.info(f"📋 Found {len(all_commands)} commands to sync")

        if all_commands:
            for cmd in all_commands:
                self.logger.debug(f"  Command: /{cmd.name} - {cmd.description}")

        # Sync slash commands globally (takes up to 1 hour)
        try:
            self.logger.info("🔄 Syncing slash commands with Discord...")
            sync_start = time.time()
            synced = await self.sync_all_application_commands()
            sync_duration = time.time() - sync_start

            log_performance(
                "command_sync",
                sync_duration,
                commands_synced=len(synced) if synced else 0,
            )
            self.logger.info(
                f"✅ Successfully synced {len(synced) if synced else 0} slash commands"
            )
        except Exception as e:
            self.logger.error(f"❌ Failed to sync commands: {e}")
            self.logger.exception("Command sync error details:")

    async def load_cogs(self, startup_logger):
        """Load all cog modules with detailed progress tracking."""
        import time

        cogs_dir = Path("cogs")

        if not cogs_dir.exists():
            startup_logger.step("Creating cogs directory (none found)", success=False)
            cogs_dir.mkdir()
            self.logger.warning("Created empty cogs directory - no extensions to load")
            return

        # Find all cog files
        cog_files = [f for f in cogs_dir.glob("*.py") if not f.name.startswith("_")]

        if not cog_files:
            startup_logger.step("No cog files found to load", success=False)
            return

        startup_logger.step(f"Found {len(cog_files)} cog files to load")

        loaded_count = 0
        # Load all Python files in cogs directory
        for cog_file in cog_files:
            cog_name = f"cogs.{cog_file.stem}"
            try:
                load_start = time.time()
                self.load_extension(cog_name)
                load_duration = time.time() - load_start

                log_performance("cog_load", load_duration, cog_name=cog_name)
                startup_logger.step(f"Loaded cog: {cog_name}")
                loaded_count += 1
            except Exception as e:
                startup_logger.step(
                    f"Failed to load cog {cog_name}: {e}", success=False
                )
                self.logger.exception(f"Cog loading error for {cog_name}:")

        self.logger.info(f"Successfully loaded {loaded_count}/{len(cog_files)} cogs")


async def main():
    """Main async entry point with comprehensive startup logging."""
    import time
    import os

    # Determine logging preset based on environment
    preset = os.getenv("LOGGING_PRESET", "development")
    if preset not in ["development", "production", "minimal"]:
        preset = "development"

    # Setup comprehensive logging
    startup_logger = setup_logging_preset(preset)
    logger = get_logger("main")

    # Start the startup sequence
    startup_logger.start_sequence(6, "Discord Bot Initialization")

    overall_start = time.time()

    # Step 1: Load configuration
    try:
        config_start = time.time()
        config = get_config()
        config_duration = time.time() - config_start

        log_performance("config_load", config_duration)
        startup_logger.step("Configuration loaded and validated")
        logger.info(f"Loaded config with {len(config.__dict__)} settings")
    except Exception as e:
        startup_logger.step(f"Configuration failed: {e}", success=False)
        logger.exception("Configuration loading failed:")
        return

    # Step 2: Test database connection
    try:
        db_start = time.time()
        db_health = await db_manager.health_check()
        db_duration = time.time() - db_start

        log_performance("database_health_check", db_duration)
        if db_health["status"] == "healthy":
            startup_logger.step("Database connection verified")
        else:
            startup_logger.step(
                f"Database health check: {db_health['message']}", success=False
            )
            logger.warning(f"Database status: {db_health}")
    except Exception as e:
        startup_logger.step(f"Database connection failed: {e}", success=False)
        logger.exception("Database health check failed:")

    # Step 3: Create bot instance
    try:
        bot_start = time.time()
        bot = DiscordBot()
        bot.startup_time = overall_start
        bot_creation_duration = time.time() - bot_start

        log_performance("bot_creation", bot_creation_duration)
        startup_logger.step("Bot instance created with intents configured")
    except Exception as e:
        startup_logger.step(f"Bot creation failed: {e}", success=False)
        logger.exception("Bot instance creation failed:")
        return

    # Step 4: Load all cogs
    try:
        await bot.load_cogs(startup_logger)
        startup_logger.step("All available cogs processed")
    except Exception as e:
        startup_logger.step(f"Cog loading failed: {e}", success=False)
        logger.exception("Cog loading failed:")

    # Step 5: Connect to Discord
    try:
        startup_logger.step("Connecting to Discord...")
        connect_start = time.time()
        await bot.start(config.discord_token)
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user (Ctrl+C)")
        startup_logger.step("Bot stopped by user interrupt", success=False)
    except Exception as e:
        connect_duration = (
            time.time() - connect_start if "connect_start" in locals() else 0
        )
        log_performance("discord_connection_failed", connect_duration, error=str(e))
        startup_logger.step(f"Discord connection failed: {e}", success=False)
        logger.exception("Bot connection failed:")
    finally:
        # Step 6: Cleanup
        try:
            await bot.close()
            startup_logger.step("Bot shutdown completed")
            startup_logger.complete("Bot session ended")
        except Exception:
            logger.exception("Error during bot cleanup:")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
