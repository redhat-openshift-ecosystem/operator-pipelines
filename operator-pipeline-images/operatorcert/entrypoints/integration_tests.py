"""
Integration tests for the operator-pipelines project
"""

import argparse
import logging
import sys
from pathlib import Path

from operatorcert.integration.runner import run_integration_tests

LOGGER = logging.getLogger("operator-cert")


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--image", "-i", help="Skip image build and use alternate container image"
    )
    parser.add_argument(
        "directory", type=Path, help="operator-pipelines project directory"
    )
    parser.add_argument("config_file", type=Path, help="Path to the yaml config file")

    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    """
    Set up the logging configuration for the application.

    Args:
        verbose (bool): If True, set the logging level to DEBUG; otherwise, set it to INFO.

    This function configures the logging format and level for the application, allowing for
    detailed debug messages when verbose mode is enabled.
    """

    logging.basicConfig(
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        level=logging.DEBUG if verbose else logging.INFO,
    )


def main() -> int:
    """
    Main function for integration tests runner
    """
    args = parse_args()
    setup_logging(args.verbose)

    # Logic
    return run_integration_tests(args.directory, args.config_file, args.image)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
