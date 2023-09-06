"""
Logging configuration for operator-cert.
"""
import logging
import sys
from typing import Any

STREAM_FORMAT = "%(asctime)s [%(name)s] %(levelname)s %(message)s"


def setup_logger(level: str = "INFO", log_format: Any = None) -> Any:
    """
    Set up and configure 'operator-cert' logger.

    Args:
        level (str, optional): Logging level. Defaults to "INFO".
        log_format (Any, optional): Logging message format. Defaults to None.

    Returns:
        Any: Logger object
    """

    logger = logging.getLogger("operator-cert")
    logger.propagate = False
    logger.setLevel(level)

    if log_format is None:
        log_format = STREAM_FORMAT

    stream_formatter = logging.Formatter(log_format)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    return logger
