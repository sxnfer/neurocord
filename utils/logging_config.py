"""Enhanced logging configuration with color formatting and structured output."""

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import colorama
    from colorama import Back, Fore, Style

    colorama.init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False

    # Fallback empty objects if colorama not available
    class _ColorFallback:
        def __getattr__(self, name):
            return ""

    Fore = Style = Back = _ColorFallback()


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding and enhanced readability."""

    # Color scheme for different log levels
    LEVEL_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + Back.WHITE,
    }

    # Component colors for better visual separation
    COMPONENT_COLORS = {
        "timestamp": Fore.BLUE + Style.DIM,
        "name": Fore.MAGENTA,
        "level": Style.BRIGHT,
        "message": Style.NORMAL,
        "separator": Fore.WHITE + Style.DIM,
    }

    def __init__(self, use_colors: bool = True, detailed: bool = False):
        """Initialize formatter with color and detail options."""
        self.use_colors = use_colors and COLORS_AVAILABLE
        self.detailed = detailed

        if detailed:
            # Detailed format for file logging
            fmt = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(funcName)-15s:%(lineno)-4d | %(message)s"
        else:
            # Clean format for console
            fmt = "%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s"

        super().__init__(fmt, datefmt="%H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and enhanced structure."""
        # Get the basic formatted message
        formatted = super().format(record)

        if not self.use_colors:
            return formatted

        # Apply colors to different components
        level_color = self.LEVEL_COLORS.get(record.levelno, "")

        # Split the formatted message to colorize parts
        parts = formatted.split(" | ")
        if len(parts) >= 4:
            timestamp, name, level, message = (
                parts[0],
                parts[1],
                parts[2],
                " | ".join(parts[3:]),
            )

            colored_parts = [
                f"{self.COMPONENT_COLORS['timestamp']}{timestamp}{Style.RESET_ALL}",
                f"{self.COMPONENT_COLORS['name']}{name}{Style.RESET_ALL}",
                f"{level_color}{self.COMPONENT_COLORS['level']}{level}{Style.RESET_ALL}",
                f"{level_color}{message}{Style.RESET_ALL}",
            ]

            separator = f"{self.COMPONENT_COLORS['separator']} | {Style.RESET_ALL}"
            return separator.join(colored_parts)

        # Fallback: just colorize by level
        return f"{level_color}{formatted}{Style.RESET_ALL}"


class StartupLogger:
    """Special logger for startup sequence with progress tracking."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.start_time = datetime.now()
        self.steps_completed = 0
        self.total_steps = 0

    def start_sequence(self, total_steps: int, title: str = "Bot Startup"):
        """Initialize startup sequence."""
        self.total_steps = total_steps
        self.steps_completed = 0
        self.start_time = datetime.now()

        if COLORS_AVAILABLE:
            header = f"\n{Fore.CYAN + Style.BRIGHT}{'=' * 60}"
            title_line = f"{Fore.CYAN + Style.BRIGHT}🚀 {title.upper()} 🚀"
            footer = f"{'=' * 60}{Style.RESET_ALL}\n"
            self.logger.info(f"{header}\n{title_line:^60}\n{footer}")
        else:
            self.logger.info(f"\n{'=' * 60}")
            self.logger.info(f"🚀 {title.upper()} 🚀")
            self.logger.info(f"{'=' * 60}\n")

    def step(self, message: str, success: bool = True):
        """Log a startup step with progress indication."""
        self.steps_completed += 1
        progress = f"[{self.steps_completed}/{self.total_steps}]"

        if COLORS_AVAILABLE:
            if success:
                icon = f"{Fore.GREEN}✅{Style.RESET_ALL}"
                step_info = f"{Fore.BLUE + Style.DIM}{progress}{Style.RESET_ALL}"
            else:
                icon = f"{Fore.RED}❌{Style.RESET_ALL}"
                step_info = f"{Fore.RED + Style.DIM}{progress}{Style.RESET_ALL}"
        else:
            icon = "✅" if success else "❌"
            step_info = progress

        self.logger.info(f"{icon} {step_info} {message}")

    def complete(self, message: str = "Startup completed successfully!"):
        """Complete startup sequence with timing information."""
        elapsed = (datetime.now() - self.start_time).total_seconds()

        if COLORS_AVAILABLE:
            completion = f"\n{Fore.GREEN + Style.BRIGHT}🎉 {message}"
            timing = f"{Fore.BLUE + Style.DIM}Total startup time: {elapsed:.2f}s{Style.RESET_ALL}\n"
            self.logger.info(f"{completion}\n{timing}")
        else:
            self.logger.info(f"\n🎉 {message}")
            self.logger.info(f"Total startup time: {elapsed:.2f}s\n")


class DiscordBotLogger:
    """Enhanced logging system for Discord bot with multiple handlers and formatters."""

    def __init__(self, name: str = "DiscordBot"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.startup_logger: Optional[StartupLogger] = None

    def setup_logging(
        self,
        level: int = logging.INFO,
        file_logging: bool = True,
        console_colors: bool = True,
        detailed_file_logs: bool = True,
        log_file: str = "bot.log",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
    ) -> StartupLogger:
        """Setup comprehensive logging with multiple handlers."""

        # Clear any existing handlers
        self.logger.handlers.clear()
        self.logger.setLevel(level)

        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(use_colors=console_colors, detailed=False)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler with rotation
        if file_logging:
            log_path = Path(log_file)
            log_path.parent.mkdir(exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)  # Always debug level for files
            file_formatter = ColoredFormatter(
                use_colors=False, detailed=detailed_file_logs
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

        # Error file handler (separate file for errors)
        if file_logging:
            error_file = log_path.parent / f"error_{log_path.name}"
            error_handler = logging.handlers.RotatingFileHandler(
                error_file,
                maxBytes=max_file_size // 2,
                backupCount=backup_count,
                encoding="utf-8",
            )
            error_handler.setLevel(logging.ERROR)
            error_formatter = ColoredFormatter(use_colors=False, detailed=True)
            error_handler.setFormatter(error_formatter)
            self.logger.addHandler(error_handler)

        # Create startup logger
        self.startup_logger = StartupLogger(self.logger)

        return self.startup_logger

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Get a child logger with consistent formatting."""
        if name:
            return logging.getLogger(f"{self.name}.{name}")
        return self.logger

    def get_startup_logger(self) -> StartupLogger:
        """Get the startup logger for initialization sequences."""
        if not self.startup_logger:
            raise RuntimeError("Logging not configured. Call setup_logging() first.")
        return self.startup_logger


# Global logger instance
discord_logger = DiscordBotLogger()


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a properly configured logger."""
    return discord_logger.get_logger(name)


def log_function_call(func_name: str, **kwargs) -> None:
    """Deprecated: previously used for debugging; no longer referenced."""
    return None


def log_performance(operation: str, duration: float, **metadata) -> None:
    """Log performance metrics for operations."""
    logger = get_logger("performance")
    meta_str = ", ".join(f"{k}={v}" for k, v in metadata.items())
    logger.info(f"Performance: {operation} took {duration:.3f}s | {meta_str}")


def log_user_interaction(user_id: int, guild_id: int, command: str, **details) -> None:
    """Log user interactions for monitoring and debugging."""
    logger = get_logger("interactions")
    detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
    logger.info(f"User {user_id} in guild {guild_id} used /{command} | {detail_str}")


# Configuration presets
LOGGING_PRESETS = {
    "development": {
        "level": logging.DEBUG,
        "console_colors": True,
        "detailed_file_logs": True,
        "file_logging": True,
    },
    "production": {
        "level": logging.INFO,
        "console_colors": False,
        "detailed_file_logs": True,
        "file_logging": True,
    },
    "minimal": {
        "level": logging.WARNING,
        "console_colors": True,
        "detailed_file_logs": False,
        "file_logging": False,
    },
}


def setup_logging_preset(preset: str = "development") -> StartupLogger:
    """Setup logging using a predefined preset."""
    if preset not in LOGGING_PRESETS:
        raise ValueError(
            f"Unknown preset '{preset}'. Available: {list(LOGGING_PRESETS.keys())}"
        )

    config = LOGGING_PRESETS[preset]
    return discord_logger.setup_logging(**config)
