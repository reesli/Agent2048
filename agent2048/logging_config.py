"""Logging infrastructure for Agent2048.

Provides structured logging with Rich console integration.
Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
"""

import logging
from pathlib import Path
from rich.logging import RichHandler


_LOGGER_NAME = "agent2048"
_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    """Get or create the singleton Agent2048 logger.

    Logs to Rich console (for TUI/CLI) and optionally to a file.
    """
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger(_LOGGER_NAME)
    _logger.setLevel(logging.DEBUG)

    # Rich console handler — pretty output for terminal.
    rich_handler = RichHandler(
        show_time=True,
        show_level=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    rich_handler.setLevel(logging.INFO)
    _logger.addHandler(rich_handler)

    # File handler — for debugging and audit trails.
    log_dir = Path.home() / ".config" / "agent2048" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "agent2048.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    _logger.addHandler(file_handler)

    # Prevent double logging through root logger.
    _logger.propagate = False

    return _logger


def set_level(level: int) -> None:
    """Set the logging level for the console handler."""
    logger = get_logger()
    for handler in logger.handlers:
        if isinstance(handler, RichHandler):
            handler.setLevel(level)
            break


logger = get_logger()
