"""Configure test suite for given operator by adding/removing labels"""
import argparse
import logging
import os
import re
from typing import Any, Dict

from github import Auth, Github
from operatorcert.github import add_or_remove_labels
from operatorcert.logger import setup_logger
from operatorcert.utils import get_repo_config

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Github cli tool to manage required tests."
    )
    parser.add_argument(
        "--github-host-url",
        default="https://api.github.com",
        help="The GitHub host, default: https://api.github.com",
    )
    parser.add_argument(
        "--repo-config-file",
        required=True,
        help="A path to a repository configuration file.",
    )

    parser.add_argument(
        "--operator-name",
        required=True,
        help="Name of the operator to be tested.",
    )

    parser.add_argument(
        "--pull-request-url",
        required=True,
        help="The GitHub pull request URL where we want to edit labels.",
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def can_ignore_test(
    test: Dict[str, Any],
    operator_name: str,
) -> bool:
    """
    Check if test can be ignored for given operator.

    Args:
        test (Dict[str, Any]): A test configuration to check.
        operator_name (str): An operator name to check.

    Returns:
        bool: True if test can be ignored, False otherwise.
    """
    test_name = test.get("name")
    LOGGER.debug("Checking test %s", test)

    for ignored_operator in test.get("ignore_operators", []):
        LOGGER.debug("Checking ignored operator %s", ignored_operator)
        if not re.match(ignored_operator, operator_name):
            continue
        LOGGER.info(
            "Operator %s is ignored for test %s",
            operator_name,
            test_name,
        )
        return True
    return False


def configure_test_suite(args: argparse.Namespace, github: Github) -> None:
    """
    Configure test suite for given operator by adding/removing labels that
    control which tests are relevant.

    Args:
        args (argparse.Namespace): CLI arguments.
        github (Github): Github API client.
    """
    config = get_repo_config(args.repo_config_file)
    tests = config.get("tests", [])
    skip_labels = set()
    operator_name = args.operator_name
    for test in tests:
        test_name = test.get("name")
        LOGGER.debug("Checking test %s", test_name)
        skip_test = can_ignore_test(test, operator_name)
        if skip_test:
            skip_labels.add(f"tests/skip/{test_name}")

    add_or_remove_labels(github, args.pull_request_url, list(skip_labels), [], True)


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

    github_auth = Auth.Token(os.environ.get("GITHUB_TOKEN"))
    github = Github(auth=github_auth)
    configure_test_suite(args, github)


if __name__ == "__main__":  # pragma: no cover
    main()
