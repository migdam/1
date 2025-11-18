"""Logging system for AI Library & Knowledge Engine."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        """Format log record with colors."""
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        return super().format(record)


def setup_logger(
    name: str = "ai_library",
    log_file: Optional[str] = None,
    level: str = "INFO",
    console: bool = True,
    max_bytes: int = 10485760,  # 10 MB
    backup_count: int = 5,
    format_string: Optional[str] = None
) -> logging.Logger:
    """Set up logger with file and console handlers.

    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console: Whether to log to console
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        format_string: Custom format string

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Clear existing handlers
    logger.handlers.clear()

    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Default format
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )

    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(format_string)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Console handler with colors
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Shorter format for console
        console_format = "%(asctime)s - %(levelname)s - %(message)s"
        console_formatter = ColoredFormatter(
            console_format,
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str = "ai_library") -> logging.Logger:
    """Get existing logger or create a new one.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # If logger has no handlers, set up a basic one
    if not logger.handlers:
        setup_logger(name)

    return logger


class LoggerContext:
    """Context manager for temporary logger configuration."""

    def __init__(self, logger: logging.Logger, level: str):
        """Initialize context with logger and temporary level.

        Args:
            logger: Logger instance
            level: Temporary logging level
        """
        self.logger = logger
        self.new_level = getattr(logging, level.upper(), logging.INFO)
        self.old_level = None

    def __enter__(self):
        """Enter context and change logger level."""
        self.old_level = self.logger.level
        self.logger.setLevel(self.new_level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original logger level."""
        self.logger.setLevel(self.old_level)


class PerformanceLogger:
    """Logger for tracking performance metrics."""

    def __init__(self, logger: logging.Logger):
        """Initialize performance logger.

        Args:
            logger: Base logger instance
        """
        self.logger = logger
        self.start_times = {}

    def start(self, operation: str) -> None:
        """Start timing an operation.

        Args:
            operation: Name of the operation
        """
        self.start_times[operation] = datetime.now()
        self.logger.debug(f"Started: {operation}")

    def end(self, operation: str, extra_info: str = "") -> float:
        """End timing an operation and log duration.

        Args:
            operation: Name of the operation
            extra_info: Additional information to log

        Returns:
            Duration in seconds
        """
        if operation not in self.start_times:
            self.logger.warning(f"No start time found for: {operation}")
            return 0.0

        start_time = self.start_times.pop(operation)
        duration = (datetime.now() - start_time).total_seconds()

        log_msg = f"Completed: {operation} in {duration:.2f}s"
        if extra_info:
            log_msg += f" - {extra_info}"

        self.logger.info(log_msg)
        return duration

    def log_stats(self, operation: str, **stats) -> None:
        """Log statistics for an operation.

        Args:
            operation: Name of the operation
            **stats: Statistics to log
        """
        stats_str = ", ".join(f"{k}={v}" for k, v in stats.items())
        self.logger.info(f"{operation}: {stats_str}")


# Global logger instance
_logger_instance = None


def init_global_logger(config=None) -> logging.Logger:
    """Initialize global logger from configuration.

    Args:
        config: Configuration object

    Returns:
        Logger instance
    """
    global _logger_instance

    if config:
        log_file = config.get('logging.file', './logs/ai_library.log')
        level = config.get('logging.level', 'INFO')
        console = config.get('logging.console', True)
        max_size = config.get('logging.max_size', 10485760)
        backup_count = config.get('logging.backup_count', 5)
    else:
        log_file = './logs/ai_library.log'
        level = 'INFO'
        console = True
        max_size = 10485760
        backup_count = 5

    _logger_instance = setup_logger(
        name="ai_library",
        log_file=log_file,
        level=level,
        console=console,
        max_bytes=max_size,
        backup_count=backup_count
    )

    return _logger_instance


def get_global_logger() -> logging.Logger:
    """Get or create global logger instance.

    Returns:
        Logger instance
    """
    global _logger_instance

    if _logger_instance is None:
        _logger_instance = setup_logger("ai_library")

    return _logger_instance
