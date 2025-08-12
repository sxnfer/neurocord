"""Ask command cog that uses OpenAI to answer user questions."""

import time
from typing import Optional

import nextcord
from nextcord import SlashOption
from nextcord.ext import commands

import openai

from utils.config import get_config
from utils.logging_config import get_logger, log_performance, log_user_interaction


logger = get_logger("ask")


class Ask(commands.Cog):
    """Provide an `/ask` command that queries an OpenAI model."""

    def __init__(self, bot: commands.Bot, model_name: Optional[str] = None):
        self.bot = bot
        config = get_config()
        # Initialize async OpenAI client
        self.client = openai.AsyncOpenAI(api_key=config.openai_api_key)
        # Default to gpt-5-mini as requested; fall back handled at runtime
        self.model = model_name or "gpt-5-mini"
        logger.info(f"Ask cog initialized with model: {self.model}")

    @nextcord.slash_command(
        name="ask",
        description="Ask the bot a question and get an AI-powered response",
    )
    async def ask(
        self,
        interaction: nextcord.Interaction,
        prompt: str = SlashOption(description="Your question or instruction"),
        private: bool = SlashOption(
            description="Send the response privately (ephemeral)",
            required=False,
            default=True,
        ),
    ):
        """Handle the /ask command using OpenAI chat completions."""
        operation_start = time.time()

        # Log interaction
        log_user_interaction(
            interaction.user.id,
            interaction.guild.id if interaction.guild else 0,
            "ask",
            prompt_length=len(prompt),
            private=private,
        )

        # Defer early to avoid 3s timeout
        try:
            await interaction.response.defer(ephemeral=private)
        except Exception as e:
            logger.warning(f"Failed to defer interaction for /ask: {e}")
            return

        try:
            # Build messages
            system_message = {
                "role": "system",
                "content": (
                    "You are a concise, helpful assistant for a Discord bot. "
                    "Answer clearly and keep responses under 1200 characters when possible."
                ),
            }
            user_message = {"role": "user", "content": prompt.strip()}

            # Call OpenAI
            api_start = time.time()
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[system_message, user_message],
                    temperature=0.7,
                )
            except openai.APIError as api_err:
                # If model is invalid/unavailable, try a sensible fallback
                logger.warning(
                    f"Primary model '{self.model}' failed, attempting fallback: {api_err}"
                )
                fallback_model = "gpt-4o-mini"
                response = await self.client.chat.completions.create(
                    model=fallback_model,
                    messages=[system_message, user_message],
                    temperature=0.7,
                )
                self.model = fallback_model
            api_duration = time.time() - api_start
            log_performance("ask_openai_call", api_duration, model=self.model)

            # Extract content
            content = (
                response.choices[0].message.content if response.choices else ""
            )
            if not content:
                content = "Sorry, I couldn't generate a response. Please try again."

            # Discord hard limit safeguard (2000 chars). Prefer a soft limit slightly lower
            max_len = 1900
            if len(content) > max_len:
                content = content[: max_len - 20].rstrip() + "\n… (truncated)"

            await interaction.followup.send(content, ephemeral=private)

            total_duration = time.time() - operation_start
            log_performance("ask_command_total", total_duration, success=True)

        except Exception as e:
            total_duration = time.time() - operation_start
            log_performance("ask_command_total", total_duration, success=False, error=str(e))
            logger.exception(f"Unexpected error in /ask: {e}")

            embed = nextcord.Embed(
                title="❌ Ask Failed",
                description=(
                    "An error occurred while processing your request. "
                    "Please try again later."
                ),
                color=nextcord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


def setup(bot: commands.Bot):
    """Required setup function for cogs."""
    bot.add_cog(Ask(bot))
    logger.info("Ask cog loaded successfully")


