"""Detect which operator bundles are affected by a PR"""
import argparse
import json
import logging
import os
import pathlib
import re
from typing import Tuple, Optional, Set, Dict, List
from operator_repo import Repo as OperatorRepo

from github import Auth, Github
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Detect which operator bundles are affected by a PR"
    )
    parser.add_argument(
        "--repo-path",
        type=pathlib.Path,
        help="Path to the root of the local clone of the repo",
        required=True,
    )
    parser.add_argument(
        "--base-repo-path",
        type=pathlib.Path,
        help="Path to the root of the local clone of the base branch of the PR",
        required=True,
    )
    parser.add_argument(
        "--pr-url",
        type=str,
        help="URL of the corresponding pull request",
        required=True,
    )
    parser.add_argument(
        "--output-file",
        type=pathlib.Path,
        help="Path to a json file where results will be stored",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def github_pr_affected_files(pr_url: str) -> set[str]:
    """
    Return the names of all files affected by the given pull request.
    Will talk to the Github API authenticating using the token in the
    GITHUB_TOKEN environment variable or using an unauthenticated request
    if the GITHUB_TOKEN variable is not set.
    Args:
        pr_url: URL of the pull request

    Returns:
        A set containing the names of all the affected files
    """
    pr_url_re = re.compile(
        r"https?://[^/]+/(?P<namespace>[^/]+)/(?P<reponame>[^/]+)/pull/(?P<pr_number>[0-9]+)"
    )
    pr_url_match = pr_url_re.match(pr_url)
    if pr_url_match is None:
        raise ValueError(f"Invalid pull request URL: {pr_url}")
    repo_namespace = pr_url_match.group("namespace")
    repo_name = pr_url_match.group("reponame")
    pr_number = int(pr_url_match.group("pr_number"))
    gh_token = os.environ.get("GITHUB_TOKEN")
    if gh_token:
        gh_auth = Auth.Token(gh_token)
        github = Github(auth=gh_auth)
    else:
        github = Github()
    gh_repo = github.get_repo(f"{repo_namespace}/{repo_name}")
    gh_pr = gh_repo.get_pull(pr_number)
    # Extract all unique names of changed files in the PR
    return {x.filename for x in gh_pr.get_files()}


def _find_owner(path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Given a relative file name within an operator repo, return a pair
    (operator_name, bundle_version) indicating what bundle the file belongs to.
    If the file is outside a bundle directory, the returned bundle_version will
    be None.
    If the file is outside an operator directory, both operator_name and
    bundle_version will be None.
    Args:
        path: Path to the file
    Returns:
        (operator_name, bundle_version) Operator/bundle the files belongs to
    """
    # split the relative filename into a tuple of individual components
    filename_parts = pathlib.Path(path).parts
    if len(filename_parts) < 3 or filename_parts[0] != "operators":
        # path is outside an operator directory
        return None, None
    _, detected_operator_name, detected_bundle_version, *rest = filename_parts
    if len(rest) < 1:
        # inside an operator but not in a bundle (i.e.: the ci.yaml file)
        return detected_operator_name, None
    return detected_operator_name, detected_bundle_version


def detect_changed_operators(  # pylint: disable=too-many-locals,too-many-branches
    repo_path: pathlib.Path,
    base_path: pathlib.Path,
    pr_url: str,
) -> Dict[str, List[str]]:
    """
    Given two snapshots of an operator repository returns a dictionary
    containing information on what operators and bundles have changed and how.
    Args:
        repo_path: Path to the root of the snapshot of the operator repository
            after the changes
        base_path: Path to the root of the snapshot of the operator repository
            before the changes
        pr_url: URL of the corresponding GitHub pull request

    Returns:
        A dictionary containing the following fields:
            - extra_files: list of the names of the files that were affected
                by the change but do not belong to an operator or a bundle
            - affected_operators: list of the names of all operators affected
                by the changes
            - added_operators: list of the names of new operators that were
                added by the changes
            - modified_operators: list of the names of existing operators that
                were modified by the changes
            - deleted_operators: list of the names of operators that were
                removed by the changes
            - affected_bundles: list of the names of all bundles affected by
                the changes
            - added_bundles: list of the names of new bundles that were added
                by the changes
            - modified_bundles: list of the names of existing bundles that
                were modified by the changes
            - deleted_bundles: list of the names of bundles that were deleted
                by the changes
    """

    LOGGER.debug("Detecting changes in repo at %s", repo_path)

    # Phase 1: using the diff between PR head and base, detect which bundles
    # have been affected by the PR

    affected_files = github_pr_affected_files(pr_url)

    LOGGER.debug("Affected files: %s", affected_files)

    non_operator_files: Set[str] = set()
    all_affected_bundles: Dict[str, Set[Optional[str]]] = {}

    for filename in affected_files:
        operator_name, bundle_version = _find_owner(filename)
        if operator_name is None:
            non_operator_files.add(filename)
        else:
            all_affected_bundles.setdefault(operator_name, set()).add(
                # This is None for files within an operator but outside
                # a bundle (i.e.: ci.yaml)
                bundle_version
            )

    LOGGER.debug("Affected bundles: %s", all_affected_bundles)
    LOGGER.debug("Files not belonging to an operator: %s", non_operator_files)

    # Phase 2: Now that we know which operators and bundles have changed, determine exactly
    # what was added, modified or removed

    added_operators: Set[str] = set()
    modified_operators: Set[str] = set()
    deleted_operators: Set[str] = set()
    added_bundles: Set[Tuple[str, str]] = set()
    modified_bundles: Set[Tuple[str, str]] = set()
    deleted_bundles: Set[Tuple[str, str]] = set()

    head_repo = OperatorRepo(repo_path)
    base_repo = OperatorRepo(base_path)

    for (  # pylint: disable=too-many-nested-blocks
        operator_name,
        operator_bundles,
    ) in all_affected_bundles.items():
        base_operator = None
        head_operator = None
        if head_repo.has(operator_name):
            head_operator = head_repo.operator(operator_name)
            if base_repo.has(operator_name):
                base_operator = base_repo.operator(operator_name)
                modified_operators.add(operator_name)
            else:
                added_operators.add(operator_name)
        else:
            deleted_operators.add(operator_name)
        for bundle_version in operator_bundles:
            if bundle_version is not None:
                if head_operator is None:
                    # The operator is not present in the new commit, therefore
                    # all of its bundles must have been removed too
                    deleted_bundles.add((operator_name, bundle_version))
                else:
                    if head_operator.has(bundle_version):
                        if base_operator is not None and base_operator.has(
                            bundle_version
                        ):
                            modified_bundles.add((operator_name, bundle_version))
                        else:
                            added_bundles.add((operator_name, bundle_version))
                    else:
                        deleted_bundles.add((operator_name, bundle_version))

    LOGGER.debug("Added operators: %s", added_operators)
    LOGGER.debug("Modified operators: %s", modified_operators)
    LOGGER.debug("Deleted operators: %s", deleted_operators)
    LOGGER.debug("Added bundles: %s", added_bundles)
    LOGGER.debug("Modified bundles: %s", modified_bundles)
    LOGGER.debug("Deleted bundles: %s", deleted_bundles)

    return {
        "extra_files": list(non_operator_files),
        "affected_operators": list(
            added_operators | modified_operators | deleted_operators
        ),
        "added_operators": list(added_operators),
        "modified_operators": list(modified_operators),
        "deleted_operators": list(deleted_operators),
        "affected_bundles": [
            f"{x}/{y}" for x, y in added_bundles | modified_bundles | deleted_bundles
        ],
        "added_bundles": [f"{x}/{y}" for x, y in added_bundles],
        "modified_bundles": [f"{x}/{y}" for x, y in modified_bundles],
        "deleted_bundles": [f"{x}/{y}" for x, y in deleted_bundles],
    }


def main() -> None:
    """
    Main function
    """
    # Args
    parser = setup_argparser()
    args = parser.parse_args()

    # logging
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    # Logic
    result = detect_changed_operators(
        args.repo_path,
        args.base_repo_path,
        args.pr_url,
    )

    if args.output_file:
        with args.output_file.open(mode="w", encoding="utf-8") as output_file:
            json.dump(result, output_file)
    else:
        print(json.dumps(result))


if __name__ == "__main__":  # pragma: no cover
    main()
