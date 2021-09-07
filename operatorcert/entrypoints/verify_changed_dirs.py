import argparse
import logging
import sys

from operatorcert import (
    get_files_added_in_pr,
    verify_changed_files_location,
    get_repo_and_org_from_github_url,
)


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Verify, if only expected directories are changed by submission"
    )
    parser.add_argument("--operator-name", help="Unique name of the operator package")
    parser.add_argument("--bundle-version", help="Operator Bundle version")
    parser.add_argument(
        # Github webhook payload contains it in path pull_request.head.label
        "--pr-head-label",
        help="Label of the branch to be merged. Eg. User:branch-name",
    )
    parser.add_argument(
        "--git-repo-url",
        help="Github repository URL",
    )
    parser.add_argument("--repository", help="Base branch repository name")
    parser.add_argument("--base-branch", help="Base branch of the PR", default="main")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def main() -> None:
    # Args
    parser = setup_argparser()
    args = parser.parse_args()

    # logging
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    logging.basicConfig(level=log_level)

    # Logic
    organization, repository = get_repo_and_org_from_github_url(args.git_repo_url)

    changed_files = get_files_added_in_pr(
        organization, repository, args.base_branch, args.pr_head_label
    )

    verify_changed_files_location(
        changed_files, args.operator_name, args.bundle_version
    )


if __name__ == "__main__":
    main()
