"""Watch2gether commands for Discord bot."""

import asyncio
import time
from typing import Optional

import aiohttp
import nextcord
from nextcord import SlashOption
from nextcord.ext import commands

from utils.config import get_config
from utils.database import db_manager
from utils.logging_config import get_logger, log_performance, log_user_interaction

logger = get_logger("watch_together")


class WatchTogether(commands.Cog):
    """Watch2gether functionality for creating synchronized viewing rooms."""

    def __init__(self, bot):
        self.bot = bot
        logger.info("WatchTogether cog initialized successfully")

    @nextcord.slash_command(
        name="watch", description="Create or get Watch2gether room for the server"
    )
    async def watch_command(
        self,
        interaction: nextcord.Interaction,
        url: Optional[str] = SlashOption(
            description="Optional video URL to preload in the room", default=None
        ),
    ):
        """Create or retrieve Watch2gether room with 24-hour guild persistence."""
        operation_start = time.time()

        # Log user interaction
        log_user_interaction(
            interaction.user.id,
            interaction.guild.id,
            "watch",
            has_preload_url=bool(url),
        )

        # Defer response immediately to prevent timeout (public by default)
        try:
            await interaction.response.defer()
        except Exception as e:
            logger.warning(
                f"Failed to defer interaction for user {interaction.user.id}: {e}"
            )
            return

        try:
            # Guard: guild-only command
            if not interaction.guild:
                await interaction.followup.send(
                    "This command can only be used in servers.", ephemeral=False
                )
                return

            # Check for existing active room first
            existing_room = await db_manager.get_active_watch_room(interaction.guild.id)
            is_recovery = False  # Track if this is a recovery scenario

            if existing_room:
                # Validate if the existing room still exists
                room_url = existing_room["room_url"]
                logger.info(
                    f"Validating existing room for guild {interaction.guild.id}: {room_url}"
                )

                try:
                    is_room_valid = await self.validate_room_exists(room_url)
                except Exception as validation_error:
                    logger.error(
                        f"Room validation failed unexpectedly: {validation_error}"
                    )
                    # If validation fails, assume room is still valid to avoid false positives
                    is_room_valid = True

                if is_room_valid:
                    # Room exists and is still valid
                    logger.info(
                        f"Existing room validated successfully for guild {interaction.guild.id}"
                    )
                    embed = nextcord.Embed(
                        title="🎬 Watch2gether Room",
                        description="Your server already has an active Watch2gether room!",
                        color=nextcord.Color.blue(),
                    )
                    embed.add_field(
                        name="Room URL",
                        value=existing_room["room_url"],
                        inline=False,
                    )
                    embed.add_field(
                        name="Created",
                        value=f"<t:{int(existing_room['created_at'].timestamp())}:R>",
                        inline=True,
                    )
                    embed.add_field(
                        name="Created by",
                        value=f"<@{existing_room['created_by']}>",
                        inline=True,
                    )
                    embed.set_footer(text="Room expires 24 hours after creation")

                    # Existing room info should be private to the requester only
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                else:
                    # Room was deleted/invalid, clean up database and create new room
                    logger.info(
                        f"Existing room invalid for guild {interaction.guild.id}, cleaning up and creating new room"
                    )
                    is_recovery = True
                    cleanup_result = await db_manager.cleanup_invalid_watch_room(
                        interaction.guild.id
                    )
                    if cleanup_result.success:
                        logger.info(
                            f"Successfully cleaned up invalid room for guild {interaction.guild.id}"
                        )
                    else:
                        logger.warning(
                            f"Failed to cleanup invalid room: {cleanup_result.message}"
                        )

                    # Continue to create new room (don't return here)

            # No existing room or existing room was invalid, create a new one
            room_data = await self._create_watch2gether_room(url)

            if not room_data:
                embed = nextcord.Embed(
                    title="❌ Room Creation Failed",
                    description="Failed to create Watch2gether room. Please try again later.",
                    color=nextcord.Color.red(),
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                return

            # Save room to database
            save_result = await db_manager.save_watch_room(
                guild_id=interaction.guild.id,
                room_url=room_data["room_url"],
                created_by=interaction.user.id,
            )

            if not save_result.success:
                logger.error(f"Failed to save room to database: {save_result.message}")
                # Still show the room URL even if database save failed
                embed = nextcord.Embed(
                    title="⚠️ Room Created (Database Warning)",
                    description="Room created successfully, but there was an issue saving to database.",
                    color=nextcord.Color.orange(),
                )
            else:
                # Use the is_recovery flag to determine the appropriate message
                if is_recovery:
                    embed = nextcord.Embed(
                        title="🔄 Watch2gether Room Renewed",
                        description="Your previous room was no longer available, so we created a fresh one!",
                        color=nextcord.Color.orange(),
                    )
                else:
                    embed = nextcord.Embed(
                        title="✅ Watch2gether Room Created",
                        description="Your server's Watch2gether room is ready!",
                        color=nextcord.Color.green(),
                    )

            embed.add_field(
                name="Room URL",
                value=room_data["room_url"],
                inline=False,
            )

            if url:
                embed.add_field(
                    name="Preloaded Content",
                    value=url,
                    inline=False,
                )

            embed.add_field(
                name="Duration",
                value="24 hours",
                inline=True,
            )
            embed.add_field(
                name="Created by",
                value=f"<@{interaction.user.id}>",
                inline=True,
            )
            embed.set_footer(text="Share this room URL with your server members!")

            await interaction.followup.send(embed=embed, ephemeral=False)

            # Log successful operation
            total_duration = time.time() - operation_start
            log_performance("watch_command_total", total_duration, success=True)

        except Exception as e:
            total_duration = time.time() - operation_start
            log_performance(
                "watch_command_total", total_duration, success=False, error=str(e)
            )
            logger.exception(
                f"Error in watch command for user {interaction.user.id}: {e}"
            )
            embed = nextcord.Embed(
                title="❌ Unexpected Error",
                description="An unexpected error occurred while processing your request.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=False)

    @nextcord.slash_command(
        name="watch-delete",
        description="Delete your server's Watch2gether room from the bot",
    )
    async def watch_delete_command(self, interaction: nextcord.Interaction):
        """Manually delete the server's Watch2gether room from the database."""
        # Defer response immediately to prevent timeout (public)
        try:
            await interaction.response.defer()
        except Exception as e:
            logger.warning(f"Failed to defer interaction: {e}")
            return

        try:
            # Check if there's an existing room to delete
            existing_room = await db_manager.get_active_watch_room(interaction.guild.id)

            if not existing_room:
                embed = nextcord.Embed(
                    title="ℹ️ No Room Found",
                    description="Your server doesn't have an active Watch2gether room to delete.",
                    color=nextcord.Color.blue(),
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                return

            # Delete the room from database
            cleanup_result = await db_manager.cleanup_invalid_watch_room(
                interaction.guild.id
            )

            if cleanup_result.success:
                logger.info(
                    f"Manually deleted watch room for guild {interaction.guild.id} by user {interaction.user.id}"
                )
                embed = nextcord.Embed(
                    title="🗑️ Room Deleted",
                    description="Your server's Watch2gether room has been removed from the bot.\n\nYou can now use `/watch` to create a fresh room!",
                    color=nextcord.Color.green(),
                )
                embed.add_field(
                    name="Deleted Room",
                    value=existing_room["room_url"],
                    inline=False,
                )
                embed.add_field(
                    name="Originally Created",
                    value=f"<t:{int(existing_room['created_at'].timestamp())}:R>",
                    inline=True,
                )
                embed.add_field(
                    name="Originally Created by",
                    value=f"<@{existing_room['created_by']}>",
                    inline=True,
                )
            else:
                logger.error(
                    f"Failed to delete watch room for guild {interaction.guild.id}: {cleanup_result.message}"
                )
                embed = nextcord.Embed(
                    title="❌ Deletion Failed",
                    description="Failed to delete the Watch2gether room. Please try again later.",
                    color=nextcord.Color.red(),
                )

            await interaction.followup.send(embed=embed, ephemeral=False)

        except Exception as e:
            logger.error(f"Error in watch-delete command: {e}")
            embed = nextcord.Embed(
                title="❌ Unexpected Error",
                description="An unexpected error occurred while deleting the room.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=False)

    async def validate_room_exists(self, room_url: str) -> bool:
        """Check if Watch2gether room still exists and is accessible."""
        try:
            # Extract streamkey from room URL
            if not room_url.startswith("https://w2g.tv/rooms/"):
                logger.warning(f"Invalid room URL format: {room_url}")
                return False

            streamkey = room_url.split("/")[-1]
            if not streamkey:
                logger.warning(f"Could not extract streamkey from URL: {room_url}")
                return False

            # Check room status by trying to access the actual room page
            # Quick validation check; guard against tests patching ClientTimeout
            try:
                timeout = aiohttp.ClientTimeout(total=5)
            except Exception:
                timeout = None
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Check if the room page is accessible
                async with session.get(room_url) as response:
                    logger.info(
                        f"Room validation for {streamkey}: HTTP {response.status}"
                    )

                    if response.status == 200:
                        # Room page exists and is accessible
                        logger.info(
                            f"Room validation for {streamkey}: valid (room page accessible)"
                        )
                        return True
                    elif response.status == 404:
                        logger.info(
                            f"Room {streamkey} not found (404) - room was deleted"
                        )
                        return False
                    else:
                        logger.warning(
                            f"Room validation returned status {response.status} for {streamkey}"
                        )
                        # For other status codes (like 503, 502), assume room might still be valid
                        # to avoid false positives during temporary service issues
                        return True

        except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
            logger.warning(f"Room validation timeout for {room_url}")
            # On timeout, assume room is still valid to avoid false positives
            return True
        except aiohttp.ClientError as e:
            logger.warning(f"HTTP client error during room validation: {e}")
            return True  # Conservative approach
        except Exception as e:
            logger.error(f"Unexpected error validating room {room_url}: {e}")
            return True  # Conservative approach

    async def _create_watch2gether_room(
        self, preload_url: Optional[str] = None
    ) -> Optional[dict]:
        """Create a new Watch2gether room via API."""
        try:
            config = get_config()

            # Check if API key is configured
            if not config.watch2gether_api_key:
                logger.error("Watch2gether API key not configured")
                return None

            # Prepare API request data
            api_data = {"w2g_api_key": config.watch2gether_api_key}

            # Add preload URL if provided
            if preload_url:
                api_data["share"] = preload_url

            # Make API request to create room
            try:
                timeout = aiohttp.ClientTimeout(total=10)
            except Exception:
                timeout = None
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    "https://api.w2g.tv/rooms/create.json",
                    json=api_data,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status == 200:
                        room_data = await response.json()

                        # Extract the streamkey and construct room URL
                        streamkey = room_data.get("streamkey")
                        if streamkey:
                            room_url = f"https://w2g.tv/rooms/{streamkey}"
                            logger.info(
                                f"Successfully created Watch2gether room: {room_url}"
                            )

                            return {
                                "room_url": room_url,
                                "streamkey": streamkey,
                                "api_response": room_data,
                            }
                        else:
                            logger.error("No streamkey in API response")
                            return None
                    else:
                        logger.error(
                            f"Watch2gether API returned status {response.status}"
                        )
                        error_text = await response.text()
                        logger.error(f"API error response: {error_text}")
                        return None

        except aiohttp.ClientTimeout:
            logger.error("Watch2gether API request timed out")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating Watch2gether room: {e}")
            return None


def setup(bot):
    """Required setup function for cogs."""
    cog = WatchTogether(bot)
    bot.add_cog(cog)
    logger.info("WatchTogether cog added to bot successfully")
