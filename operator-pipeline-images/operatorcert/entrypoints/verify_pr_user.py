import argparse
import logging

from operatorcert import validate_user


def setup_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify if the Github user can submit the bundle"
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
    # Validate the Github user which created the PR
    validate_user(args.git_username, args.contacts)


if __name__ == "__main__":
    main()
