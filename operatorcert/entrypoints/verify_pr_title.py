import argparse
import logging

from operatorcert import parse_pr_title
from operatorcert.utils import store_results


def setup_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify, if the pull request title complies to regex")
    parser.add_argument("--pr-title", help="GitHub PR title")
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

    # Logic- verify the pr title
    bundle_name, bundle_version = parse_pr_title(args.pr_title)

    # Save the results
    results = {"bundle_name": bundle_name, "bundle_version": bundle_version}
    store_results(results)


if __name__ == "__main__":
    main()
