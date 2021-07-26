import argparse
import logging
import sys

from operatorcert import (
    get_files_changed_in_pr,
    verify_changed_files_location,
    get_repo_and_org_from_github_url,
)


def main() -> None:
    logging.basicConfig(stream=sys.stdout, level="INFO", format="%(message)s")

    parser = argparse.ArgumentParser(
        description="Determines the OCP version under test."
    )
    parser.add_argument("--operator_name", help="Unique name of the operator package")
    parser.add_argument(
        "--operator_version", help="Operator version in the semver format"
    )
    parser.add_argument(
        # Github webhook payload contains it in path pull_request.head.label
        "--pr_head_label",
        help="Label of the branch to be merged. Eg. User:branch-name",
    )
    parser.add_argument(
        "--git_repo_url",
        help="Github repository URL",
    )
    parser.add_argument("--repository", help="Base branch repository name")
    parser.add_argument("--base_branch", help="Base branch of the PR", default="main")
    args = parser.parse_args()

    organization, repository = get_repo_and_org_from_github_url(args.git_repo_url)

    changed_files = get_files_changed_in_pr(
        organization, repository, args.base_branch, args.pr_head_label
    )
    verify_changed_files_location(
        changed_files, repository, args.operator_name, args.operator_version
    )
