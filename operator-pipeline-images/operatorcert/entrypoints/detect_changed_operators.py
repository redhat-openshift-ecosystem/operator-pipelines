import argparse
import json
import logging
import pathlib
import tempfile
from typing import Tuple, Optional, Set, Dict, List
from git import Repo as GitRepo
from operator_repo import Repo as OperatorRepo

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
        help="Path to the root of the local clone of the repo",
        required=True,
    )
    parser.add_argument(
        "--head-commit", help="Commit ID for the head of the PR", required=True
    )
    parser.add_argument(
        "--base-commit", help="Commit ID for the base of the PR", required=True
    )
    parser.add_argument(
        "--output-file", help="Path to a json file where results will be stored"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def detect_changed_operators(
    repo_path: str,
    head_commit: str,
    base_commit: str,
) -> Dict[str, List[str]]:
    """
    Given an operator repository and a pair of commits, returns a dictionary
    containing information on what operators and bundles have been affected
    by the changes and how.
    Args:
        repo_path: Path to the root of the operator repository
        head_commit: Latest commit ID
        base_commit: Commit ID the changes were based upon

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

    LOGGER.debug("Detecting changes in repo at %s", repo_path)

    with tempfile.TemporaryDirectory() as repo_clone_path:
        # Phase 1: using the diff between PR head and base, detect which bundles
        # have been affected by the PR

        git_repo_head = GitRepo(repo_path)
        # Ensure the head commit is checked out (mostly needed for tests)
        git_repo_head.head.reference = git_repo_head.create_head(
            "pr_head", head_commit, force=True
        )
        git_repo_head.head.reset(index=True, working_tree=True)
        # Make a temporary clone of the repo and check out the base commit
        git_repo_base = git_repo_head.clone(repo_clone_path)
        git_repo_base.create_head("pr_head", head_commit, force=True)
        git_repo_base.head.reference = git_repo_base.create_head(
            "pr_base", base_commit, force=True
        )
        git_repo_base.head.reset(index=True, working_tree=True)

        # Extract all unique names of changed files between pr_base and pr_head, including
        # previous names for renamed files
        affected_files = {
            y
            for x in git_repo_base.heads.pr_base.commit.diff("pr_head")
            for y in (x.a_path, x.b_path)
            if y
            is not None  # According to the GitPython docs, a_path and b_path can be None
        }

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
        base_repo = OperatorRepo(repo_clone_path)

        for operator_name, operator_bundles in all_affected_bundles.items():
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
        args.head_commit,
        args.base_commit,
    )

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as output_file:
            json.dump(result, output_file)
    else:
        print(json.dumps(result))


if __name__ == "__main__":  # pragma: no cover
    main()
