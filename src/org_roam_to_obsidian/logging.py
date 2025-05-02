"""
Module for configuring structured logging using structlog.

This module provides a standardized way to configure and use structured logging
throughout the application. It ensures logs are consistent and have all necessary
context fields.
"""

import logging
import sys
from typing import Any, Callable, Mapping, MutableMapping, Tuple

import structlog
from structlog.stdlib import BoundLogger

# Type alias for structlog processors
# mypy: allow-any-generics
Processor = Callable[
    [Any, str, MutableMapping[str, Any]],
    Mapping[str, Any] | str | bytes | bytearray | Tuple[Any, ...],
]


def setup_logging(verbose: bool = False) -> None:
    """
    Configure structlog with the appropriate processors and handlers.

    Args:
        verbose: Whether to use DEBUG level logging (True) or INFO level (False)
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    # Set up standard library logging processor chain
    processors: list[Processor] = [
        # Add log level as a key to the event dict
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamps
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        # Extract context data from contextvars
        structlog.contextvars.merge_contextvars,
    ]

    if verbose:
        # Pretty printing for development mode
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # Format exceptions to provide full traceback
        processors.append(structlog.processors.format_exc_info)
        # Format as JSON for production mode/machine readability
        processors.append(structlog.processors.JSONRenderer())

    # Set up structlog to use stdlib as backend
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> BoundLogger:
    """
    Get a structured logger instance for the given name.

    Args:
        name: The name of the logger, typically __name__ of the module

    Returns:
        A configured structlog logger instance
    """
    # Get a standard logger
    # structlog.get_logger will use the factory set by structlog.configure
    return structlog.get_logger(name)  # type: ignore[no-any-return]
