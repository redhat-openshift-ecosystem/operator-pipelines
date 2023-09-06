"""Generate a markdown summary for a Tekton PipelineRun."""
import argparse
import logging
from typing import Any

from operatorcert.logger import setup_logger
from operatorcert.tekton import PipelineRun

LOGGER = logging.getLogger("operator-cert")


def parse_args() -> Any:  # pragma: no cover
    """
    Create an argument parser and parse the arguments.

    Returns:
        Any: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Construct a markdown summary for a Tekton PipelineRun."
    )
    parser.add_argument("pr_path", help="File path to a PipelineRun object")
    parser.add_argument("trs_path", help="File path to a JSON list of TaskRun objects")
    parser.add_argument(
        "--include-final-tasks",
        help="Include final tasks in the output",
        action="store_true",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser.parse_args()


def main() -> None:
    """
    Generate a markdown summary for a Tekton PipelineRun.
    """
    args = parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level, log_format="%(message)s")
    pipeline_run = PipelineRun.from_files(args.pr_path, args.trs_path)

    LOGGER.info(
        pipeline_run.markdown_summary(include_final_tasks=args.include_final_tasks)
    )


if __name__ == "__main__":  # pragma: no cover
    main()
