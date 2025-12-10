"""
Logging Configuration Module

Provides loguru-based logging configuration.
"""

import sys
from typing import Optional

from loguru import logger

__all__ = ["logger", "configure_logging"]


def configure_logging(
    level: str = "INFO",
    format: Optional[str] = None,
    colorize: bool = True,
    serialize: bool = False,
) -> None:
    """
    Configure logging

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Custom log format, None uses default format
        colorize: Whether to enable colored output
        serialize: Whether to serialize to JSON format

    Example:
        from dify_assistant.logging import configure_logging, logger

        # Use default configuration
        configure_logging()

        # Custom configuration
        configure_logging(level="DEBUG", colorize=False)

        # Use logger
        logger.info("This is an info message")
        logger.debug("Debug message with context", extra={"user": "user-123"})
    """
    # Remove default handler
    logger.remove()

    # Default format
    if format is None:
        format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # Add new handler
    logger.add(
        sys.stderr,
        format=format,
        level=level,
        colorize=colorize,
        serialize=serialize,
    )


# Export pre-configured logger instance
# Users can use it directly or call configure_logging() for custom configuration
