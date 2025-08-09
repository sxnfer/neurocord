"""Test cog to verify bot functionality."""

import nextcord
from nextcord import SlashOption
from nextcord.ext import commands

from utils.database import db_manager
from utils.embeddings import embedding_manager


class TestCommands(commands.Cog):
    """Simple test commands to verify bot is working."""

    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name="ping", description="Test if the bot is responding")
    async def ping(self, interaction: nextcord.Interaction):
        """Simple ping command to test bot responsiveness."""
        await interaction.response.send_message("🏓 Pong! Bot is working!")

    @nextcord.slash_command(name="echo", description="Echo back what you say")
    async def echo(
        self,
        interaction: nextcord.Interaction,
        message: str = SlashOption(description="Message to echo back"),
    ):
        """Echo command to test parameter handling."""
        await interaction.response.send_message(f"You said: {message}")

    @nextcord.slash_command(name="async_test", description="Test async operations")
    async def async_test(self, interaction: nextcord.Interaction):
        """Test async operations with simulated delay."""
        # Defer the response since we'll take more than 3 seconds
        await interaction.response.defer()

        # Simulate some async work
        import asyncio

        await asyncio.sleep(2)  # Simulate API call

        # Follow up with the result
        await interaction.followup.send(
            "✅ Async test completed! This took 2 seconds but didn't block other commands."
        )

    @nextcord.slash_command(name="db_test", description="Test database connection")
    async def database_test(self, interaction: nextcord.Interaction):
        """Test database connection and health."""
        # Defer the response since database calls can take time
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send(
                "This command can only be used in servers.", ephemeral=True
            )
            return

        # Test the database connection
        result = await db_manager.test_connection()

        if result.success:
            # Create a nice embed for success
            embed = nextcord.Embed(
                title="🟢 Database Connection Test",
                description=result.message,
                color=nextcord.Color.green(),
            )
            embed.add_field(name="Status", value="✅ Connected", inline=True)
            embed.add_field(name="Response Time", value="< 3 seconds", inline=True)

            # Get additional health info
            health = await db_manager.health_check()
            embed.add_field(name="Health", value=health["status"].title(), inline=True)

        else:
            # Create embed for failure
            embed = nextcord.Embed(
                title="🔴 Database Connection Test",
                description=result.message,
                color=nextcord.Color.red(),
            )
            embed.add_field(name="Status", value="❌ Failed", inline=True)

            # Add error details if available
            if result.errors:
                error_text = "\n".join(result.errors[:3])  # Show first 3 errors
                embed.add_field(
                    name="Errors", value=f"```{error_text}```", inline=False
                )

        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(
        name="embedding_test", description="Test OpenAI embedding generation"
    )
    async def embedding_test(self, interaction: nextcord.Interaction):
        """Test OpenAI embedding API connection."""
        # Defer the response since API calls can take time
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send(
                "This command can only be used in servers.", ephemeral=True
            )
            return

        # Test the embedding generation
        result = await embedding_manager.test_connection()

        if result.success:
            # Create a nice embed for success
            embed = nextcord.Embed(
                title="🟢 OpenAI Embedding Test",
                description=result.message,
                color=nextcord.Color.green(),
            )
            embed.add_field(name="Status", value="✅ Connected", inline=True)
            embed.add_field(name="Model", value="text-embedding-3-small", inline=True)

            # Show embedding dimensions from the result data
            if result.data and "embedding_dimensions" in result.data:
                dimensions = result.data["embedding_dimensions"]
                embed.add_field(name="Dimensions", value=f"{dimensions}", inline=True)

        else:
            # Create embed for failure
            embed = nextcord.Embed(
                title="🔴 OpenAI Embedding Test",
                description=result.message,
                color=nextcord.Color.red(),
            )
            embed.add_field(name="Status", value="❌ Failed", inline=True)

            # Add error details if available
            if result.errors:
                error_text = "\n".join(result.errors[:2])  # Show first 2 errors
                embed.add_field(
                    name="Errors", value=f"```{error_text}```", inline=False
                )

        await interaction.followup.send(embed=embed)


def setup(bot):
    """Required setup function for cogs."""
    bot.add_cog(TestCommands(bot))
