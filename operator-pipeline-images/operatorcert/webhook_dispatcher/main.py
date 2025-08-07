"""Main entry point for the webhook dispatcher application."""

import argparse
import asyncio
import logging

import os
import threading

from operatorcert.logger import setup_logger
from operatorcert.webhook_dispatcher.api import app
from operatorcert.webhook_dispatcher.config import DatabaseConfig, load_config
from operatorcert.webhook_dispatcher.database import init_database
from operatorcert.webhook_dispatcher.dispatcher import EventDispatcher

LOGGER = logging.getLogger("operator-cert")


def setup_argument_parser() -> argparse.ArgumentParser:
    """
    Setup argument parser for the webhook dispatcher.

    Returns:
        argparse.ArgumentParser: Argument parser instance
    """

    parser = argparse.ArgumentParser(description="GitHub Webhook Dispatcher")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser


def main() -> None:
    """
    Main function to start the webhook dispatcher application.
    """
    parser = setup_argument_parser()
    args = parser.parse_args()

    setup_logger(level="DEBUG" if args.verbose else "INFO")
    LOGGER.info("Starting an application")

    db_manager = init_database(DatabaseConfig())

    db_manager.create_tables()

    config = load_config(
        os.getenv("WEBHOOK_DISPATCHER_CONFIG", "./config/dispatcher_config.yaml")
    )

    # Open a new thread for the dispatcher
    dispatcher = EventDispatcher(config.dispatcher)

    dispatcher_thread = threading.Thread(
        target=asyncio.run, args=(dispatcher.run(),), daemon=True
    )
    dispatcher_thread.start()

    LOGGER.info("Starting API")
    app.run(
        port=int(os.environ.get("DISPATCHER_PORT", "5000")),
        host="0.0.0.0",  # nosec
    )


if __name__ == "__main__":  # pragma: no cover
    main()
