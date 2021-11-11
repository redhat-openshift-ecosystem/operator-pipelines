import logging
from typing import Any

STREAM_FORMAT = "%(asctime)s [%(name)s] %(levelname)s %(message)s"


def setup_logger(level: str = "INFO") -> Any:
    """
    Set up and configure 'operator-cert' logger.
    """
    logger = logging.getLogger("operator-cert")
    logger.propagate = False
    logger.setLevel(level)

    stream_formatter = logging.Formatter(STREAM_FORMAT)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    return logger
