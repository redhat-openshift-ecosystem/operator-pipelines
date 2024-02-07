"""Publish image and related collections in Pyxis"""
import argparse
import logging
import sys
from typing import Any

from operatorcert import pyxis
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("isv-sre-tools")


def setup_argparser() -> Any:
    """
    Setup argument parser for this script.
    """
    parser = argparse.ArgumentParser(description="Container image publisher.")

    parser.add_argument(
        "--image-identifier",
        help="Image _id to submit a new request for.",
    )
    parser.add_argument(
        "--cert-project-id",
        help="Certification project ID.",
    )
    parser.add_argument(
        "--pyxis-url",
        default="https://pyxis.engineering.redhat.com",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument(
        "--wait-for-grades",
        action="store_true",
        help="Wait for container freshness grades before submitting the request",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def submit_image_request(args: Any) -> Any:
    """
    Submit a new publish image request and wait for it to finish.

    Args:
        args (Any): CLI arguments
    """

    request = pyxis.post_image_request(
        args.pyxis_url,
        args.cert_project_id,
        args.image_identifier,
        "publish",
    )
    image_request = pyxis.wait_for_image_request(args.pyxis_url, request["_id"])
    if image_request["status"] != "completed":
        LOGGER.error(
            "Image request failed: %s - %s",
            image_request["status"],
            image_request["status_message"],
        )
        sys.exit(1)
    return image_request


def is_clair_enabled(pyxis_url: str) -> bool:
    """
    Check if Clair is enabled in the environment.

    Some environments do not have Clair enabled,
    so we need to check if it is enabled.

    Args:
        pyxis_url (str): Pyxis URL

    Returns:
        bool: True if Clair is enabled, False otherwise
    """
    return not (".qa." in pyxis_url or ".uat." in pyxis_url)


def main() -> None:
    """
    Main function
    """
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)
    if args.wait_for_grades and is_clair_enabled(args.pyxis_url):
        pyxis.wait_for_container_grades(args.pyxis_url, args.image_identifier)
    submit_image_request(args)


if __name__ == "__main__":  # pragma: no cover
    main()
