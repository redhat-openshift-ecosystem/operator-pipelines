import argparse
import logging
import requests
import sys
from typing import List
from operatorcert.utils import str_color


class InvalidChangesPath(Exception):
    """
    Exception for changes in wrong path
    """


def get_changed_files(
    organization: str, repository: str, base_branch: str, pr_head_label: str
) -> List[str]:
    compare_changes_url = (
        f"https://api.github.com/repos/{organization}/{repository}"
        f"/compare/{base_branch}...{pr_head_label}"
    )
    pr_data = requests.get(compare_changes_url).json()

    filenames = []
    for file in pr_data["files"]:
        filenames.append(file["filename"])

    return filenames


def verify_changed_files_location(
    changed_files: List[str], repository: str, operator_name: str, operator_version: str
) -> None:

    parent_path = f"{repository}/operators/{operator_name}"
    path = parent_path + "/" + operator_version
    config_path = parent_path + "/ci.yaml"

    logging.info(
        str_color(
            "blue",
            f"Changes for operator {operator_name} in version {operator_version}"
            f" are expected to be in paths: \n"
            f" -{path}/* \n"
            f" -{config_path}",
        )
    )

    wrong_changes = False
    for file_path in changed_files:
        if file_path.startswith(path):
            logging.info(str_color("green", f"Change path ok: {file_path}"))
            continue
        elif file_path == config_path:
            continue
        else:
            logging.error(str_color("red", f"Wrong change path: {file_path}"))
            wrong_changes = True

    if wrong_changes:
        raise InvalidChangesPath("There are changes in the invalid path")


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
        "--organization",
        help="Base branch repository owner name",
        default="redhat-openshift-ecosystem",
    )
    parser.add_argument(
        "--repository", help="Base branch repository name", default="operator-pipelines"
    )
    parser.add_argument("--base_branch", help="Base branch of the PR", default="main")
    args = parser.parse_args()

    changed_files = get_changed_files(
        args.organization, args.repository, args.base_branch, args.pr_head_label
    )

    verify_changed_files_location(
        changed_files, args.repository, args.operator_name, args.operator_version
    )
