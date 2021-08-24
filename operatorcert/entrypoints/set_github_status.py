import argparse
import logging
from urllib.parse import urljoin

from operatorcert import github, get_repo_and_org_from_github_url

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
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


def set_github_status(args) -> None:
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
        f"Successfully set status to {args.status} for commit {args.commit_sha} in "
        f"github repo {args.git_repo_url}"
    )


def main() -> None:
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    logging.basicConfig(level=log_level)

    set_github_status(args)


if __name__ == "__main__":
    main()
