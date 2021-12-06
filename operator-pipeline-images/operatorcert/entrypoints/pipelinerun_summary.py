import argparse
import logging
import sys

from operatorcert.tekton import PipelineRun


def parse_args() -> argparse.ArgumentParser:  # pragma: no cover
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

    return parser.parse_args()


def main() -> None:
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")

    args = parse_args()
    pr = PipelineRun.from_files(args.pr_path, args.trs_path)

    logging.info(pr.markdown_summary(include_final_tasks=args.include_final_tasks))
