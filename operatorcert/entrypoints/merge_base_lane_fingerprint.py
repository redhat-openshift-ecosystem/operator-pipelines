"""CLI: record or verify merge-time base-branch lane fingerprint snapshots."""

import argparse
import logging
import sys
from pathlib import Path

from operatorcert.logger import setup_logger
from operatorcert.merge_base_lane import (
    record_snapshot,
    verify_snapshot,
)

LOGGER = logging.getLogger("operator-cert")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record or verify a fingerprint of operator/catalog paths on the base branch."
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser(
        "record", help="Write snapshot.json from the base clone at tree-ish"
    )
    rec.add_argument(
        "--git-dir",
        required=True,
        type=Path,
        help="Path to git repository (base branch clone)",
    )
    rec.add_argument(
        "--tree-ish",
        required=True,
        help="Commit or ref to fingerprint (pipeline git_commit_base)",
    )
    rec.add_argument(
        "--operator-path",
        default="",
        help="operators/... path from detect-changes",
    )
    rec.add_argument(
        "--added-or-modified-catalog-operators",
        default="",
        help=(
            "Comma-separated entries from detect-changes "
            "added_or_modified_catalog_operators (version/operator, ...)"
        ),
    )
    rec.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to snapshot JSON file",
    )

    ver = sub.add_parser(
        "verify",
        help="Compare live upstream tip + lane fingerprint to snapshot (exit 10 on mismatch)",
    )
    ver.add_argument(
        "--git-dir",
        required=True,
        type=Path,
        help="Path to git repository (PR clone, used for fetch + ls-tree)",
    )
    ver.add_argument(
        "--git-repo-url",
        required=True,
        help="Upstream repository URL (same as pipeline git_repo_url)",
    )
    ver.add_argument(
        "--git-base-branch",
        required=True,
        help="Base branch name (e.g. main)",
    )
    ver.add_argument(
        "--snapshot-file",
        required=True,
        type=Path,
        help="Path to snapshot JSON written by record",
    )
    return parser


def main() -> None:
    """CLI entrypoint for record or verify merge-base lane fingerprint snapshots."""
    parser = _parser()
    args = parser.parse_args()
    setup_logger(level="DEBUG" if args.verbose else "INFO")
    try:
        if args.command == "record":
            record_snapshot(
                args.git_dir,
                args.tree_ish,
                args.operator_path,
                args.added_or_modified_catalog_operators,
                args.output,
            )
        elif args.command == "verify":
            rc = verify_snapshot(
                args.git_dir,
                args.git_repo_url,
                args.git_base_branch,
                args.snapshot_file,
            )
            if rc != 0:
                sys.exit(rc)
        else:
            parser.error(f"Unknown command {args.command!r}")
    except (OSError, RuntimeError, ValueError) as err:
        LOGGER.error("%s", err)
        sys.exit(1)


if __name__ == "__main__":
    main()
