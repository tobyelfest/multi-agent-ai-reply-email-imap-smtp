"""Structured logging with rotating file and console output."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def configure_logging(
    log_dir: str,
    log_level: int = logging.INFO,
    max_bytes: int = 10_485_760,   # 10 MB
    backup_count: int = 5,
) -> logging.Logger:
    """Set up a logger with console and rotating file handlers.

    Args:
        log_dir: Directory to store log files.
        log_level: Logging level (default INFO).
        max_bytes: Maximum size of a log file before rotation.
        backup_count: Number of rotated files to keep.

    Returns:
        logging.Logger: Configured logger instance.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("email_ai")
    logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplication
    if logger.handlers:
        logger.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console.setFormatter(console_format)
    logger.addHandler(console)

    # Rotating file handler
    file_path = log_path / "app.log"
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Retrieve a child logger with the given name."""
    logger = logging.getLogger("email_ai")
    if name:
        return logger.getChild(name)
    return logger
