"""Watch2gether commands for Discord bot."""

import logging
from typing import Optional

import aiohttp
import nextcord
from nextcord import SlashOption
from nextcord.ext import commands

from utils.config import get_config
from utils.database import db_manager

logger = logging.getLogger(__name__)


class WatchTogether(commands.Cog):
    """Watch2gether functionality for creating synchronized viewing rooms."""

    def __init__(self, bot):
        self.bot = bot
        logger.info("WatchTogether cog initialized")

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
        # Defer response immediately to prevent timeout
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception as e:
            logger.warning(f"Failed to defer interaction: {e}")
            return

        try:
            # Check for existing active room first
            existing_room = await db_manager.get_active_watch_room(interaction.guild.id)

            if existing_room:
                # Room exists and is still valid (within 24 hours)
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

                await interaction.followup.send(embed=embed, ephemeral=False)
                return

            # No existing room, create a new one
            room_data = await self._create_watch2gether_room(url)

            if not room_data:
                embed = nextcord.Embed(
                    title="❌ Room Creation Failed",
                    description="Failed to create Watch2gether room. Please try again later.",
                    color=nextcord.Color.red(),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
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

        except Exception as e:
            logger.error(f"Error in watch command: {e}")
            embed = nextcord.Embed(
                title="❌ Unexpected Error",
                description="An unexpected error occurred while processing your request.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

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
            timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
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
