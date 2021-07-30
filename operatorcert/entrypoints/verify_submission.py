import argparse
import logging
import sys

from operatorcert import parse_pr_title, verify_pr_uniqueness


def main() -> None:
    logging.basicConfig(stream=sys.stdout, level="INFO", format="%(message)s")

    parser = argparse.ArgumentParser(description="Verify the submission to repository")
    parser.add_argument("--pr-title", help="GitHub PR title")
    parser.add_argument("--pr-url", help="GitHub PR url")
    parser.add_argument(
        "--available-repositories",
        help="List of repository names (coma separated),"
        "with potentially duplicate PRs",
    )
    args = parser.parse_args()

    bundle_name, bundle_version = parse_pr_title(args.pr_title)

    # Validate the Github user which created the PR
    # TODO

    # Verify, that there is no other PR opened for this Bundle
    verify_pr_uniqueness(args.available_repositories, args.pr_url, bundle_name)
