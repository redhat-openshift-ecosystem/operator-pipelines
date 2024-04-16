"""Set github status for a commit"""

import argparse
import logging
from typing import Any
from urllib.parse import urljoin

from operatorcert import get_repo_and_org_from_github_url, github
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Set given github commit to a specific state"
    )
    parser.add_argument(
        "--git-repo-url",
        help="URL of the git repo",
    )
    parser.add_argument("--commit-sha", help="SHA of the commit to set status for")
    parser.add_argument(
        "--status",
        help="Status to set the commit to",
        choices=["error", "failure", "pending", "success"],
    )
    parser.add_argument("--context", default="", help="Context to add to the status")
    parser.add_argument(
        "--description", default="", help="Description to add to the status"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def set_github_status(args: Any) -> None:
    """
    Set github status for a commit

    Args:
        args (Any): CLI arguments
    """
    org, repo = get_repo_and_org_from_github_url(args.git_repo_url)
    status_uri = "/repos/{org}/{repo}/statuses/{sha}"
    post_data = {
        "context": args.context,
        "description": args.description,
        "state": args.status,
    }
    github.post(
        urljoin(
            "https://api.github.com",
            status_uri.format(org=org, repo=repo, sha=args.commit_sha),
        ),
        post_data,
    )

    LOGGER.info(
        "Successfully set status to %s for commit %s in github repo %s",
        args.status,
        args.commit_sha,
        args.git_repo_url,
    )


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

    set_github_status(args)


if __name__ == "__main__":  # pragma: no cover
    main()
