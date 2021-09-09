import argparse
import logging

from operatorcert import parse_pr_title, verify_pr_uniqueness, validate_user
from operatorcert.utils import store_results


def setup_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify the submission to repository")
    parser.add_argument("--pr-title", help="GitHub PR title")
    parser.add_argument("--pr-url", help="GitHub PR url")
    parser.add_argument(
        "--available-repositories",
        help="List of repository names (coma separated),"
        "with potentially duplicate PRs",
        default="redhat-openshift-ecosystem/operator-pipelines-test",
    )
    parser.add_argument(
        "--git-username", help="Username of account which submitted the bundle"
    )
    parser.add_argument(
        "--contacts", help="List of users allowed to submit bundle", nargs="+"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def main() -> None:
    # Args
    parser = setup_argparser()
    args = parser.parse_args()

    # Logging
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    logging.basicConfig(level=log_level)

    # Logic
    bundle_name, bundle_version = parse_pr_title(args.pr_title)

    # Validate the Github user which created the PR
    validate_user(args.git_username, args.contacts)

    # Verify, that there is no other PR opened for this Bundle
    repos = args.available_repositories.split(",")
    verify_pr_uniqueness(repos, args.pr_url, bundle_name)

    # Save the results
    results = {"bundle_name": bundle_name, "bundle_version": bundle_version}
    store_results(results)


if __name__ == "__main__":
    main()
