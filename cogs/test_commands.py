"""Test cog to verify bot functionality."""

import nextcord
from nextcord import SlashOption
from nextcord.ext import commands

from utils.database import db_manager


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


def setup(bot):
    """Required setup function for cogs."""
    bot.add_cog(TestCommands(bot))
