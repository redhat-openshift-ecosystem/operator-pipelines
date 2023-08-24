import argparse
import json
from typing import Any, Dict

from operatorcert.logger import setup_logger
from operator_repo.utils import load_yaml
import logging
import pathlib

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:
    """
    Argument parser setup

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Get the review from repo maintainers or approve PR if PR author is also one of the reviewers"
    )
    parser.add_argument(
        "--repo-path", help="Path to cloned operator repository", required=True
    )
    parser.add_argument(
        "--git-username", help="Github pull request author", required=True
    )
    parser.add_argument(
        "--operator-name", help="Name of the cloned operator", required=True
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output-file",
        help="Output file with results - list of the reviewers and boolean if reviewer is included in ci.yaml file",
    )

    return parser


def parse_ci_reviewer(
    repo_path: str, git_username: str, operator_name: str
) -> Dict[str, str]:
    """
    Given operator repo path, pull request GitHub author and operator name, returns boolean if
    PR author is also listed as a reviewer in the ci.yaml file, list of the reviewers in the ci.yaml file.
    Args:
        repo_path: Path to the cloned operator repository
        git_username: GitHub pull request author
        operator_name: Name of the added operator

    Returns:
        Boolean (True/False) if the pull request author is also listed as one of the reviewers
        List of all reviewers listed in the ci.yaml file
    """

    path_to_operator = pathlib.Path(repo_path) / "operators" / operator_name / "ci.yaml"
    load_ci_yaml = load_yaml(path_to_operator)
    yaml_reviewers = load_ci_yaml.get("reviewers")

    # assigning empty list in case there are no reviewers in ci.yaml
    all_reviewers = (
        [] if yaml_reviewers is None else [reviewer for reviewer in yaml_reviewers]
    )
    LOGGER.debug(f"List of all reviewers from ci.yaml file {all_reviewers}")

    # assigning false in case there are also no reviewers in ci.yaml
    is_reviewer = (
        "false"
        if yaml_reviewers is None or git_username not in yaml_reviewers
        else "true"
    )
    LOGGER.debug(f"'{git_username}' is listed as reviewer: {is_reviewer}")

    return {"all_reviewers": all_reviewers, "is_reviewer": is_reviewer}


def main():
    """
    Main func
    """
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)

    result = parse_ci_reviewer(args.repo_path, args.git_username, args.operator_name)

    if args.output_file:
        with open(args.output_file, "w") as output_file:
            json.dump(result, output_file)


if __name__ == "__main__":  # pragma: no cover
    main()
