"""Remove stale GitHub webhooks from a given repository."""

import argparse
import logging
import os
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from github import Github
from github.Hook import Hook

from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")

MAX_WEBHOOK_AGE_DAYS = 7


def remove_stale_webhooks(webhooks: Iterable[Hook]) -> int:
    """Remove webhooks older than set amount of days."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=MAX_WEBHOOK_AGE_DAYS)
    count = 0

    for webhook in webhooks:
        created_at = webhook.created_at.replace(tzinfo=timezone.utc)
        if created_at < cutoff_date:
            webhook.delete()
            count += 1

    return count


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser for this script.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Remove stale GitHub webhooks from a repository. "
            "Requires the GITHUB_TOKEN environment variable containing a token "
            "with permission to list and delete repository webhooks."
        )
    )
    parser.add_argument(
        "--repository",
        required=True,
        help="GitHub repository in org/repository format, "
        "e.g. redhat-openshift-ecosystem/operator-pipelines-test.",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def main() -> None:
    """Run stale webhook cleanup for a given repository."""
    args = setup_argparser().parse_args()
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    github_client = Github(login_or_token=os.environ["GITHUB_TOKEN"])
    all_webhooks = github_client.get_repo(args.repository).get_hooks()
    removed_count = remove_stale_webhooks(all_webhooks)

    LOGGER.info(
        "Removed %d stale GitHub webhooks from %s", removed_count, args.repository
    )


if __name__ == "__main__":  # pragma: no cover
    main()
