"""
Script for editing a labels in a pull request.
"""
import argparse
import logging
import os

from github import Auth, Github
from operatorcert.github import add_or_remove_labels
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Github cli tool to manage labels to PR."
    )
    parser.add_argument(
        "--github-host-url",
        default="https://api.github.com",
        help="The GitHub host, default: https://api.github.com",
    )
    parser.add_argument(
        "--add-labels",
        nargs="+",
        default=[],
        help="List of labels that will be added to a pull request.",
    )
    parser.add_argument(
        "--remove-labels",
        nargs="+",
        default=[],
        help="List of labels that will be removed from a pull request.",
    )
    parser.add_argument(
        "--remove-matching-namespace-labels",
        action="store_true",
        help="A flag that enables removal of existing labels with matching "
        "namespace. The namespace is parsed from --add-labels.",
    )
    parser.add_argument(
        "--pull-request-url",
        required=True,
        help="The GitHub pull request URL where we want to edit labels.",
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


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

    add_or_remove_labels(
        github,
        args.pull_request_url,
        args.add_labels,
        args.remove_labels,
        args.remove_matching_namespace_labels,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
