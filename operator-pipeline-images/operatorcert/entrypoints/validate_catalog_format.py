"""Validate catalog format for all given catalogs."""

import argparse
import logging
from subprocess import CalledProcessError
import sys

from operatorcert.logger import setup_logger
from operatorcert.utils import SplitArgs, run_command

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        argparse.ArgumentParser: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Validate catalog format for all given catalogs."
    )
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to the root of the local clone of the repo",
        required=True,
    )
    parser.add_argument(
        "--catalog-names",
        default=[],
        action=SplitArgs,
        help="List of catalog names to validate",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def validate_catalog_format(catalog_path: str, catalog_name: str) -> None:
    """
    Run `opm validate` for a given catalog.
    """
    cmd = [
        "opm",
        "validate",
        f"{catalog_path}/{catalog_name}",
    ]
    LOGGER.info("Validating catalog %s", catalog_name)
    run_command(cmd)


def main() -> None:
    """
    Main function of the script
    """
    # Args
    parser = setup_argparser()
    args = parser.parse_args()

    # Logging
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    invalid_catalogs = []

    # For each catalog validate its format
    for catalog_name in args.catalog_names:
        catalog_path = f"{args.repo_path}/catalogs"
        try:
            validate_catalog_format(catalog_path, catalog_name)
        except CalledProcessError:
            LOGGER.error("Catalog %s format is invalid", catalog_name)
            invalid_catalogs.append(catalog_name)

    if invalid_catalogs:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
