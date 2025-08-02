"""Help command for Discord bot with comprehensive command documentation."""

import logging
from typing import Dict

import nextcord
from nextcord import SlashOption
from nextcord.ext import commands

logger = logging.getLogger(__name__)


class Help(commands.Cog):
    """Help system providing comprehensive command documentation and examples."""

    def __init__(self, bot):
        self.bot = bot
        self.commands_data = self._initialize_commands_data()

    def _initialize_commands_data(self) -> Dict[str, Dict]:
        """Initialize comprehensive command data with descriptions, usage, and examples."""
        return {
            "semantic_search": {
                "category": "🔍 Semantic Search",
                "description": "Save and search content using AI-powered semantic similarity",
                "commands": {
                    "save": {
                        "description": "Save content for semantic search with AI embeddings",
                        "usage": "/save content:<your_content>",
                        "parameters": [
                            {
                                "name": "content",
                                "type": "string",
                                "required": True,
                                "description": "Content to save for later searching",
                            }
                        ],
                        "examples": [
                            "/save content:How to set up a Discord bot with Python",
                            "/save content:Meeting notes from today's standup about the new feature",
                            "/save content:Important debugging tips for async/await issues",
                        ],
                        "notes": [
                            "Content is embedded using AI for semantic search",
                            "You can save any text content up to Discord's character limit",
                            "Content is saved per server and linked to your user account",
                        ],
                    },
                    "search": {
                        "description": "Search saved content using semantic similarity (finds meaning, not just keywords)",
                        "usage": "/search query:<search_terms> [limit:<1-10>]",
                        "parameters": [
                            {
                                "name": "query",
                                "type": "string",
                                "required": True,
                                "description": "What are you looking for?",
                            },
                            {
                                "name": "limit",
                                "type": "integer",
                                "required": False,
                                "description": "Number of results (1-10, default: 5)",
                            },
                        ],
                        "examples": [
                            "/search query:python bot setup",
                            "/search query:meeting notes limit:3",
                            "/search query:debugging async code limit:10",
                        ],
                        "notes": [
                            "Uses AI to find content by meaning, not just exact keyword matches",
                            "Returns results ranked by semantic similarity percentage",
                            "Shows content preview, creator, and unique ID for each result",
                        ],
                    },
                    "delete": {
                        "description": "Delete your saved content by ID (only your own content)",
                        "usage": "/delete content_id:<uuid>",
                        "parameters": [
                            {
                                "name": "content_id",
                                "type": "string",
                                "required": True,
                                "description": "ID of content to delete (from search results)",
                            }
                        ],
                        "examples": [
                            "/delete content_id:123e4567-e89b-12d3-a456-426614174000"
                        ],
                        "notes": [
                            "You can only delete content you created",
                            "Get the content ID from /search or /my_content results",
                            "Deletion is permanent and cannot be undone",
                        ],
                    },
                    "edit": {
                        "description": "Edit your saved content and regenerate its AI embedding",
                        "usage": "/edit content_id:<uuid> new_content:<updated_content>",
                        "parameters": [
                            {
                                "name": "content_id",
                                "type": "string",
                                "required": True,
                                "description": "ID of content to edit (from search results)",
                            },
                            {
                                "name": "new_content",
                                "type": "string",
                                "required": True,
                                "description": "New content to replace the old content",
                            },
                        ],
                        "examples": [
                            "/edit content_id:123e4567-e89b-12d3-a456-426614174000 new_content:Updated meeting notes with action items"
                        ],
                        "notes": [
                            "You can only edit content you created",
                            "AI embedding is automatically regenerated for the new content",
                            "Previous content is completely replaced",
                        ],
                    },
                    "my_content": {
                        "description": "View all your saved content in this server",
                        "usage": "/my_content",
                        "parameters": [],
                        "examples": ["/my_content"],
                        "notes": [
                            "Shows up to 50 of your saved items",
                            "Displays creation date and content preview",
                            "Provides content IDs for editing or deletion",
                        ],
                    },
                },
            },
            "watch_together": {
                "category": "🎬 Watch2gether",
                "description": "Create synchronized video watching rooms for your server",
                "commands": {
                    "watch": {
                        "description": "Create or get your server's Watch2gether room (24-hour duration)",
                        "usage": "/watch [url:<video_url>]",
                        "parameters": [
                            {
                                "name": "url",
                                "type": "string",
                                "required": False,
                                "description": "Optional video URL to preload in the room",
                            }
                        ],
                        "examples": [
                            "/watch",
                            "/watch url:https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                            "/watch url:https://vimeo.com/123456789",
                        ],
                        "notes": [
                            "One room per server with 24-hour duration",
                            "If room exists and is valid, returns existing room",
                            "If room expired or invalid, creates a new one automatically",
                            "Optional video URL will be preloaded for all viewers",
                        ],
                    },
                    "watch-delete": {
                        "description": "Manually delete your server's Watch2gether room from the bot",
                        "usage": "/watch-delete",
                        "parameters": [],
                        "examples": ["/watch-delete"],
                        "notes": [
                            "Removes the room from bot's database only",
                            "The actual Watch2gether room may still exist on their servers",
                            "After deletion, you can create a fresh room with /watch",
                        ],
                    },
                },
            },
        }

    @nextcord.slash_command(
        name="help", description="Get help with bot commands and features"
    )
    async def help_command(
        self,
        interaction: nextcord.Interaction,
        command: str = SlashOption(
            description="Specific command to get help with (optional)",
            default=None,
            choices=[
                "save",
                "search",
                "delete",
                "edit",
                "my_content",
                "watch",
                "watch-delete",
            ],
        ),
        category: str = SlashOption(
            description="Show commands by category (optional)",
            default=None,
            choices=["semantic_search", "watch_together"],
        ),
    ):
        """Provide comprehensive help for bot commands."""
        await interaction.response.defer()

        try:
            if command:
                # Show specific command help
                await self._send_command_help(interaction, command)
            elif category:
                # Show category help
                await self._send_category_help(interaction, category)
            else:
                # Show general help overview
                await self._send_general_help(interaction)

        except Exception as e:
            logger.error(f"Error in help command: {e}")
            embed = nextcord.Embed(
                title="❌ Help Error",
                description="An error occurred while generating help information.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

    async def _send_general_help(self, interaction: nextcord.Interaction):
        """Send general help overview with all categories."""
        embed = nextcord.Embed(
            title="🤖 Bot Help",
            description="Welcome to the Discord Bot with Semantic Search and Watch2gether features!",
            color=nextcord.Color.blue(),
        )

        # Add category summaries
        for category_key, category_data in self.commands_data.items():
            command_count = len(category_data["commands"])
            command_list = ", ".join(
                [f"`/{cmd}`" for cmd in category_data["commands"].keys()]
            )

            embed.add_field(
                name=category_data["category"],
                value=f"{category_data['description']}\n**Commands ({command_count}):** {command_list}",
                inline=False,
            )

        embed.add_field(
            name="📚 Getting Detailed Help",
            value=(
                "• `/help command:<command_name>` - Detailed help for a specific command\n"
                "• `/help category:<category_name>` - All commands in a category\n"
                "• `/help` - This overview"
            ),
            inline=False,
        )

        embed.add_field(
            name="🚀 Quick Start",
            value=(
                "1. **Save content**: `/save content:Your important notes`\n"
                "2. **Search it later**: `/search query:important notes`\n"
                "3. **Watch together**: `/watch` to create a room for your server"
            ),
            inline=False,
        )

        embed.set_footer(
            text="Use /help command:<name> for detailed examples and usage"
        )
        await interaction.followup.send(embed=embed)

    async def _send_category_help(
        self, interaction: nextcord.Interaction, category: str
    ):
        """Send help for a specific category."""
        if category not in self.commands_data:
            embed = nextcord.Embed(
                title="❌ Category Not Found",
                description=f"Category '{category}' not found.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
            return

        category_data = self.commands_data[category]
        embed = nextcord.Embed(
            title=category_data["category"],
            description=category_data["description"],
            color=nextcord.Color.green(),
        )

        # Add each command in the category
        for cmd_name, cmd_data in category_data["commands"].items():
            usage_text = f"**Usage:** `{cmd_data['usage']}`\n{cmd_data['description']}"
            if cmd_data.get("examples"):
                usage_text += f"\n**Example:** `{cmd_data['examples'][0]}`"

            embed.add_field(
                name=f"/{cmd_name}",
                value=usage_text,
                inline=False,
            )

        embed.set_footer(
            text=f"Use /help command:<name> for detailed examples • {len(category_data['commands'])} commands in this category"
        )
        await interaction.followup.send(embed=embed)

    async def _send_command_help(self, interaction: nextcord.Interaction, command: str):
        """Send detailed help for a specific command."""
        # Find the command in our data
        cmd_data = None
        category_name = None

        for cat_key, cat_data in self.commands_data.items():
            if command in cat_data["commands"]:
                cmd_data = cat_data["commands"][command]
                category_name = cat_data["category"]
                break

        if not cmd_data:
            embed = nextcord.Embed(
                title="❌ Command Not Found",
                description=f"Command '{command}' not found. Use `/help` to see all available commands.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
            return

        # Create detailed command help
        embed = nextcord.Embed(
            title=f"📖 /{command}",
            description=cmd_data["description"],
            color=nextcord.Color.blue(),
        )

        # Add usage
        embed.add_field(
            name="📝 Usage",
            value=f"`{cmd_data['usage']}`",
            inline=False,
        )

        # Add parameters if any
        if cmd_data.get("parameters"):
            param_text = ""
            for param in cmd_data["parameters"]:
                required_text = "**Required**" if param["required"] else "*Optional*"
                param_text += f"• **{param['name']}** ({param['type']}) - {required_text}\n  {param['description']}\n"

            embed.add_field(
                name="⚙️ Parameters",
                value=param_text,
                inline=False,
            )

        # Add examples
        if cmd_data.get("examples"):
            examples_text = "\n".join(
                [f"`{example}`" for example in cmd_data["examples"]]
            )
            embed.add_field(
                name="💡 Examples",
                value=examples_text,
                inline=False,
            )

        # Add notes
        if cmd_data.get("notes"):
            notes_text = "\n".join([f"• {note}" for note in cmd_data["notes"]])
            embed.add_field(
                name="ℹ️ Important Notes",
                value=notes_text,
                inline=False,
            )

        embed.set_footer(text=f"Category: {category_name} • Use /help for all commands")
        await interaction.followup.send(embed=embed)


def setup(bot):
    """Required setup function for cogs."""
    bot.add_cog(Help(bot))
    logger.info("Help cog loaded successfully")
