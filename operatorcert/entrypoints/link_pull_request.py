import argparse
import base64
import json
import logging
import os
from typing import Any, Dict, List
from urllib.parse import urljoin

import magic
from operatorcert import pyxis
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="CLI tool for linking PR to test results."
    )

    parser.add_argument(
        "--pyxis-url",
        default="https://catalog.redhat.com/api/containers/",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument(
        "--test-result-id", help="Certification test result ID", required=True
    )
    parser.add_argument(
        "--pull-request-url",
        help="A link to Github pull request",
        required=True,
    )
    parser.add_argument(
        "--pull-request-status",
        help="A status of Github pull request",
        required=True,
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def link_pr_to_test_results(
    pyxis_url: str, test_result_id: str, pull_request_url: str, status: str
) -> Dict[str, Any]:
    """
    Link a pull request to test results

    Args:
        pyxis_url (str): Pyxis API base URL
        test_result_id (str): Test result internal ID
        pull_request_url (str): Github pull request URL
        status (str): Current status of the pull request

    Raises:
        ValueError: An exception is raised when invalid PR url is given

    Returns:
        Dict[str, Any]: Pyxis API json response
    """
    test_result_url = urljoin(
        pyxis_url,
        f"v1/projects/certification/test-results/id/{test_result_id}",
    )
    pr_id = pull_request_url.split("/")[-1]
    try:
        pr_id = int(pr_id)
    except ValueError:
        raise ValueError(f"Invalid ID in pull request link: {pull_request_url}")

    data = {"pull_request": {"status": status, "url": pull_request_url, "id": pr_id}}

    return pyxis.patch(test_result_url, data)


def main():
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(log_level)

    link_pr_to_test_results(
        args.pyxis_url,
        args.test_result_id,
        args.pull_request_url,
        args.pull_request_status,
    )


if __name__ == "__main__":
    main()
