"""
Entrypoint module for community-pipelines prow tests
"""
import logging
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def main() -> None:
    """
    Main function for initializing prow tests
    """
    setup_logger()
    LOGGER.info("Testing prow")


if __name__ == "__main__":  # pragma: no cover
    main()
