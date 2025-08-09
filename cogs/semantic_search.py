"""Semantic search commands for Discord bot."""

import time
from uuid import UUID

import nextcord
from nextcord import SlashOption
from nextcord.ext import commands

from utils.database import db_manager
from utils.embeddings import embedding_manager
from utils.logging_config import get_logger, log_performance, log_user_interaction

logger = get_logger("semantic_search")


class SemanticSearch(commands.Cog):
    """Semantic search functionality for saving and searching content."""

    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name="save", description="Save content for semantic search")
    async def save_content(
        self,
        interaction: nextcord.Interaction,
        content: str = SlashOption(description="Content to save for later searching"),
    ):
        """Save content with semantic embedding."""
        operation_start = time.time()

        # Log user interaction
        log_user_interaction(
            interaction.user.id,
            interaction.guild.id,
            "save",
            content_length=len(content),
        )

        # Defer response immediately to prevent timeout
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
                    "This command can only be used in servers.",
                    ephemeral=True,
                )
                return

            # Generate embedding for the content
            embedding_start = time.time()
            embedding = await embedding_manager.generate_embedding(content)
            embedding_duration = time.time() - embedding_start

            log_performance(
                "embedding_generation", embedding_duration, content_length=len(content)
            )

            if not embedding:
                logger.error(
                    f"Embedding generation failed for user {interaction.user.id}"
                )
                embed = nextcord.Embed(
                    title="❌ Embedding Failed",
                    description="Failed to generate embedding for your content. Please try again.",
                    color=nextcord.Color.red(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Save to database
            save_start = time.time()
            result = await db_manager.save_content(
                content=content,
                embedding=embedding,
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
            )
            save_duration = time.time() - save_start

            log_performance("content_save", save_duration, content_length=len(content))

            if result.success:
                total_duration = time.time() - operation_start
                log_performance("save_command_total", total_duration, success=True)
                logger.info(
                    f"Successfully saved content for user {interaction.user.id} (ID: {result.data.get('id', 'Unknown')})"
                )

                # Success embed
                embed = nextcord.Embed(
                    title="✅ Content Saved",
                    description="Your content has been saved for semantic search!",
                    color=nextcord.Color.green(),
                )
                embed.add_field(
                    name="Content Preview",
                    value=content[:100] + "..." if len(content) > 100 else content,
                    inline=False,
                )
                embed.add_field(
                    name="Content ID",
                    value=result.data.get("id", "Unknown"),
                    inline=True,
                )
                embed.add_field(
                    name="Embedding Dimensions",
                    value=str(len(embedding)),
                    inline=True,
                )

            else:
                total_duration = time.time() - operation_start
                log_performance("save_command_total", total_duration, success=False)
                logger.error(
                    f"Save failed for user {interaction.user.id}: {result.message}"
                )

                # Error embed
                embed = nextcord.Embed(
                    title="❌ Save Failed",
                    description=result.message,
                    color=nextcord.Color.red(),
                )
                if result.errors:
                    error_text = "\n".join(result.errors[:3])
                    embed.add_field(
                        name="Errors", value=f"```{error_text}```", inline=False
                    )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            total_duration = time.time() - operation_start
            log_performance(
                "save_command_total", total_duration, success=False, error=str(e)
            )
            logger.exception(
                f"Unexpected error in save command for user {interaction.user.id}: {e}"
            )
            embed = nextcord.Embed(
                title="❌ Unexpected Error",
                description="An unexpected error occurred while saving your content.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

    @nextcord.slash_command(
        name="search", description="Search saved content semantically"
    )
    async def search_content(
        self,
        interaction: nextcord.Interaction,
        query: str = SlashOption(description="What are you looking for?"),
        limit: int = SlashOption(
            description="Number of results (1-10)", default=5, min_value=1, max_value=10
        ),
    ):
        """Search for semantically similar content."""
        # Defer response immediately to prevent timeout
        try:
            await interaction.response.defer()
        except Exception as e:
            logger.warning(f"Failed to defer interaction: {e}")
            return

        try:
            # Guard: guild-only command
            if not interaction.guild:
                await interaction.followup.send(
                    "This command can only be used in servers.",
                    ephemeral=True,
                )
                return

            # Generate embedding for the search query
            query_embedding = await embedding_manager.generate_embedding(query)
            if not query_embedding:
                embed = nextcord.Embed(
                    title="❌ Search Failed",
                    description="Failed to process your search query. Please try again.",
                    color=nextcord.Color.red(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Search database
            results = await db_manager.search_content(
                query_embedding=query_embedding,
                guild_id=interaction.guild.id,
                limit=limit,
                min_similarity=0.1,  # 10% minimum similarity
            )

            if not results:
                embed = nextcord.Embed(
                    title="🔍 No Results Found",
                    description=f"No content found similar to: **{query}**",
                    color=nextcord.Color.yellow(),
                )
                embed.add_field(
                    name="Tip",
                    value="Try different keywords or save more content first!",
                    inline=False,
                )
                await interaction.followup.send(embed=embed)
                return

            # Create results embed
            embed = nextcord.Embed(
                title="🔍 Search Results",
                description=f"Found {len(results)} results for: **{query}**",
                color=nextcord.Color.blue(),
            )

            for i, result in enumerate(results):
                content_preview = result.content.content_preview
                similarity_percent = f"{result.percentage_match:.1f}%"
                user_mention = f"<@{result.content.user_id}>"

                embed.add_field(
                    name=f"#{i + 1} - {similarity_percent} match",
                    value=f"**Content:** {content_preview}\n**Saved by:** {user_mention}\n**ID:** `{result.content.id}`",
                    inline=False,
                )

            embed.set_footer(
                text=f"Showing top {len(results)} results • Use /delete <id> to remove your content"
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in search command: {e}")
            embed = nextcord.Embed(
                title="❌ Search Error",
                description="An unexpected error occurred during search.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

    @nextcord.slash_command(name="delete", description="Delete your saved content")
    async def delete_content(
        self,
        interaction: nextcord.Interaction,
        content_id: str = SlashOption(
            description="ID of content to delete (from search results)"
        ),
    ):
        """Delete user's own saved content."""
        await interaction.response.defer()

        try:
            # Guard: guild-only command
            if not interaction.guild:
                await interaction.followup.send(
                    "This command can only be used in servers.",
                    ephemeral=True,
                )
                return

            # Validate UUID format
            try:
                content_uuid = UUID(content_id)
            except ValueError:
                embed = nextcord.Embed(
                    title="❌ Invalid ID",
                    description="Please provide a valid content ID from search results.",
                    color=nextcord.Color.red(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Delete from database
            result = await db_manager.delete_content(
                content_id=content_uuid, user_id=interaction.user.id
            )

            if result.success:
                embed = nextcord.Embed(
                    title="✅ Content Deleted",
                    description=result.message,
                    color=nextcord.Color.green(),
                )
            else:
                embed = nextcord.Embed(
                    title="❌ Delete Failed",
                    description=result.message,
                    color=nextcord.Color.red(),
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in delete command: {e}")
            embed = nextcord.Embed(
                title="❌ Delete Error",
                description="An unexpected error occurred while deleting content.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

    @nextcord.slash_command(name="edit", description="Edit your saved content")
    async def edit_content(
        self,
        interaction: nextcord.Interaction,
        content_id: str = SlashOption(
            description="ID of content to edit (from search results)"
        ),
        new_content: str = SlashOption(
            description="New content to replace the old content"
        ),
    ):
        """Edit user's own saved content."""
        await interaction.response.defer()

        try:
            # Guard: guild-only command
            if not interaction.guild:
                await interaction.followup.send(
                    "This command can only be used in servers.",
                    ephemeral=True,
                )
                return

            # Validate UUID format
            try:
                content_uuid = UUID(content_id)
            except ValueError:
                embed = nextcord.Embed(
                    title="❌ Invalid ID",
                    description="Please provide a valid content ID from search results.",
                    color=nextcord.Color.red(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Generate new embedding
            new_embedding = await embedding_manager.generate_embedding(new_content)
            if not new_embedding:
                embed = nextcord.Embed(
                    title="❌ Embedding Failed",
                    description="Failed to generate embedding for new content. Please try again.",
                    color=nextcord.Color.red(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Update in database
            result = await db_manager.edit_content(
                content_id=content_uuid,
                new_content=new_content,
                new_embedding=new_embedding,
                user_id=interaction.user.id,
            )

            if result.success:
                embed = nextcord.Embed(
                    title="✅ Content Updated",
                    description=result.message,
                    color=nextcord.Color.green(),
                )
                embed.add_field(
                    name="New Content Preview",
                    value=new_content[:100] + "..."
                    if len(new_content) > 100
                    else new_content,
                    inline=False,
                )
            else:
                embed = nextcord.Embed(
                    title="❌ Edit Failed",
                    description=result.message,
                    color=nextcord.Color.red(),
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in edit command: {e}")
            embed = nextcord.Embed(
                title="❌ Edit Error",
                description="An unexpected error occurred while editing content.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

    @nextcord.slash_command(
        name="my_content", description="View all your saved content"
    )
    async def my_content(
        self,
        interaction: nextcord.Interaction,
    ):
        """Show user's own saved content."""
        await interaction.response.defer()

        try:
            # Guard: guild-only command
            if not interaction.guild:
                await interaction.followup.send(
                    "This command can only be used in servers.",
                    ephemeral=True,
                )
                return

            # Get user's content directly from database
            user_content_list = await db_manager.get_user_content(
                user_id=interaction.user.id, guild_id=interaction.guild.id, limit=50
            )

            if not user_content_list:
                embed = nextcord.Embed(
                    title="📝 Your Content",
                    description="You haven't saved any content yet. Use `/save` to get started!",
                    color=nextcord.Color.yellow(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Create results embed
            embed = nextcord.Embed(
                title="📝 Your Saved Content",
                description=f"You have {len(user_content_list)} saved items",
                color=nextcord.Color.blue(),
            )

            for i, content in enumerate(user_content_list[:10]):  # Show max 10
                content_preview = content.content_preview
                created_date = (
                    content.created_at.strftime("%Y-%m-%d")
                    if content.created_at
                    else "Unknown"
                )

                embed.add_field(
                    name=f"#{i + 1} - Saved {created_date}",
                    value=f"**Content:** {content_preview}\n**ID:** `{content.id}`",
                    inline=False,
                )

            if len(user_content_list) > 10:
                embed.set_footer(
                    text=f"Showing first 10 of {len(user_content_list)} items • Use /search to find specific content"
                )
            else:
                embed.set_footer(
                    text="Use /delete <id> to remove content • /edit <id> to modify content"
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in my_content command: {e}")
            embed = nextcord.Embed(
                title="❌ Content Retrieval Error",
                description="An unexpected error occurred while retrieving your content.",
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed)


def setup(bot):
    """Required setup function for cogs."""
    bot.add_cog(SemanticSearch(bot))
