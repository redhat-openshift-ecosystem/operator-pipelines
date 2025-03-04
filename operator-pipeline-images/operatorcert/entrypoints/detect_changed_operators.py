"""Detect which operator bundles are affected by a PR"""

import argparse
import json
import logging
import os
import pathlib
import re
from typing import Optional

from github import Auth, Github
from operatorcert.logger import setup_logger
from operatorcert.operator_repo import Repo as OperatorRepo
from operatorcert.parsed_file import (
    AffectedBundleCollection,
    AffectedCatalogCollection,
    AffectedCatalogOperatorCollection,
    AffectedOperatorCollection,
    ParserResults,
    ParserRules,
)

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


def is_operator_bundle_dir(
    operator_name: str,
    bundle_version: str,
    head_repo: OperatorRepo,
    base_repo: OperatorRepo,
) -> tuple[bool, bool]:
    """
    Check if provided operator and bundle exist in either the head or base repo

    Returns a tuple of two booleans, the first indicating if the operator exists
    and the second indicating if the bundle exists.

    Args:
        operator_name (str): Operator name given by the directory name
        bundle_version (str): A bundle version given by the directory name
        head_repo (OperatorRepo): Git repository with the head state
        base_repo (OperatorRepo): Git repository with the base state

    Returns:
        tuple[bool, bool]: A tuple of two booleans indicating if the operator
        and bundle exist in either the head or base repo
    """
    # Check if the operator and bundle exist in either the head or base repo
    is_operator = False
    is_bundle = False
    for repo in [head_repo, base_repo]:
        if repo.has(operator_name):
            is_operator = True
            if repo.operator(operator_name).has(bundle_version):
                is_bundle = True
    return is_operator, is_bundle


def is_catalog_operator_dir(
    catalog_name: str,
    catalog_operator: str,
    head_repo: OperatorRepo,
    base_repo: OperatorRepo,
) -> bool:
    """
    Check if provided catalog and operator exist in either the head or base repo

    Args:
        catalog_name (str): A catalog name given by the directory name
        catalog_operator (str): A catalog operator given by the directory name
        head_repo (OperatorRepo): Git repository with the head state
        base_repo (OperatorRepo): Git repository with the base state

    Returns:
        bool: A boolean indicating if the catalog and operator exist in either
        the head or base repo
    """
    # Check if the catalog and operator exist in either the head or base repo
    for repo in [head_repo, base_repo]:
        if repo.has_catalog(catalog_name):
            if repo.catalog(catalog_name).has(catalog_operator):
                return True
    return False


def _find_directory_owner(
    path: str, head_repo: OperatorRepo, base_repo: OperatorRepo
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Given a relative file name within an operator repo, return a tuple
    (operator_name, bundle_version, catalog, catalog_operator) indicating what
    bundle and operator catalog the file belongs to.
    If the file is outside a bundle or catalog directory, the returned
    bundle_version or catalog_operator will be None.
    If the file is outside an operator or catalog directory, all returns will be None.
    Args:
        path: Path to the file
        head_repo: OperatorRepo object representing the head state of the repo
        base_repo: OperatorRepo object representing the base state of the repo
    Returns:
        (operator_name, bundle_version, catalog_name, catalog_operator)
        Operator/bundle, Catalog/operator the files belongs to
    """

    # split the relative filename into a tuple of individual components
    filename_parts = pathlib.Path(path).parts
    if len(filename_parts) >= 3 and filename_parts[0] == "operators":
        # inside an operator directory
        is_operator, is_bundle = is_operator_bundle_dir(
            filename_parts[1], filename_parts[2], head_repo, base_repo
        )
        if is_operator and is_bundle:
            return filename_parts[1], filename_parts[2], None, None
        if is_operator:
            # path is inside an operator but outside a bundle
            # (i.e.: ci.yaml, catalog-templates, Makefile)
            return filename_parts[1], None, None, None
    if len(filename_parts) >= 3 and filename_parts[0] == "catalogs":
        if is_catalog_operator_dir(
            filename_parts[1], filename_parts[2], head_repo, base_repo
        ):
            return None, None, filename_parts[1], filename_parts[2]
    # path is outside an operator or catalog directory
    return None, None, None, None


def _affected_bundles_and_operators_from_files(
    affected_files: set[str], head_repo: OperatorRepo, base_repo: OperatorRepo
) -> tuple[dict[str, set[Optional[str]]], dict[str, set[Optional[str]]], set[str]]:
    """
    Group a given set of file names depending on the operator, bundle,
    catalog and operator catalog they belong to

    Args:
        affected_files: set of files names to parse
        head_repo: OperatorRepo object representing the head state of the repo
        base_repo: OperatorRepo object representing the base state of the repo

    Returns:
        A tuple containing:
        - a dictionary mapping operator names to the set of bundles affected
          (or None if there are files for that operator that do not belong
          to a bundle)
        - a dictionary mapping catalog names to the set of operator affected
          (or None if there are files for that operator that do not belong
          to a bundle)
        - a set of file names that do not belong to an operator or catalog
    """
    extra_files: set[str] = set()
    all_affected_bundles: dict[str, set[Optional[str]]] = {}
    all_affected_catalog_operators: dict[str, set[Optional[str]]] = {}

    for filename in affected_files:
        (
            operator_name,
            bundle_version,
            catalog_name,
            catalog_operator,
        ) = _find_directory_owner(filename, head_repo, base_repo)
        if operator_name is None and catalog_name is None:
            extra_files.add(filename)
        elif operator_name is not None:
            all_affected_bundles.setdefault(operator_name, set()).add(
                # This is None for files within an operator but outside
                # a bundle (i.e.: ci.yaml)
                bundle_version
            )
        elif catalog_name is not None:
            all_affected_catalog_operators.setdefault(catalog_name, set()).add(
                catalog_operator
            )
    return all_affected_bundles, all_affected_catalog_operators, extra_files


def detect_changed_operators(
    head_repo: OperatorRepo,
    base_repo: OperatorRepo,
    all_affected_bundles: dict[str, set[Optional[str]]],
) -> AffectedOperatorCollection:
    """
    Given two snapshots of an operator repository returns a dictionary
    of changed operators

    Args:
        head_repo (OperatorRepo): A snapshot of the operator repository after the changes
        base_repo (OperatorRepo): A snapshot of the operator repository before the changes
        all_affected_bundles (dict[str, set[Optional[str]]]): A dictionary mapping operator

    Returns:
        AffectedOperatorCollection: An object with added, modified and deleted operators
    """
    # determine exactly what was added, modified or removed
    affected_operators = AffectedOperatorCollection()

    affected_operators.added = {
        operator
        for operator in all_affected_bundles
        if head_repo.has(operator) and not base_repo.has(operator)
    }
    affected_operators.modified = {
        operator
        for operator in all_affected_bundles
        if head_repo.has(operator) and base_repo.has(operator)
    }
    affected_operators.deleted = {
        operator
        for operator in all_affected_bundles
        if not head_repo.has(operator) and base_repo.has(operator)
    }

    LOGGER.debug("Affected operators: %s", affected_operators)

    return affected_operators


def detect_changed_operator_bundles(
    head_repo: OperatorRepo,
    base_repo: OperatorRepo,
    all_affected_bundles: dict[str, set[Optional[str]]],
) -> AffectedBundleCollection:
    """
    Given two snapshots of an operator repository returns a dictionary
    of changed operator bundles

    Args:
        head_repo (OperatorRepo): A snapshot of the operator repository after the changes
        base_repo (OperatorRepo): A snapshot of the operator repository before the changes
        all_affected_bundles (dict[str, set[Optional[str]]]): A dictionary mapping operator

    Returns:
        AffectedBundleCollection: An object with added, modified and deleted operator bundles
    """
    # determine exactly what was added, modified or removed
    affected_bundles = AffectedBundleCollection()

    non_null_bundles = {
        (operator, bundle)
        for operator, bundles in all_affected_bundles.items()
        for bundle in bundles
        if bundle is not None
    }

    affected_bundles.added = {
        (operator, bundle)
        for operator, bundle in non_null_bundles
        if head_repo.has(operator)
        and head_repo.operator(operator).has(bundle)
        and not (base_repo.has(operator) and base_repo.operator(operator).has(bundle))
    }
    affected_bundles.modified = {
        (operator, bundle)
        for operator, bundle in non_null_bundles
        if head_repo.has(operator)
        and base_repo.has(operator)
        and head_repo.operator(operator).has(bundle)
        and base_repo.operator(operator).has(bundle)
    }
    affected_bundles.deleted = {
        (operator, bundle)
        for operator, bundle in non_null_bundles
        if (not head_repo.has(operator) and base_repo.has(operator))
        or (
            not head_repo.operator(operator).has(bundle)
            and base_repo.operator(operator).has(bundle)
        )
    }

    LOGGER.debug("Affected bundles: %s", affected_bundles)

    return affected_bundles


def detect_changed_catalog_operators(
    head_repo: OperatorRepo,
    base_repo: OperatorRepo,
    all_affected_catalog_operators: dict[str, set[Optional[str]]],
) -> AffectedCatalogOperatorCollection:
    """
    Given two snapshots of an operator repository returns a dictionary
    of changed catalog operators

    Args:
        head_repo (OperatorRepo): A snapshot of the operator repository after the changes
        base_repo (OperatorRepo): A snapshot of the operator repository before the changes
        all_affected_bundles (dict[str, set[Optional[str]]]): A dictionary mapping catalogs

    Returns:
        AffectedCatalogOperatorCollection: An object with added, modified and deleted
        catalog operators
    """
    affected_catalog_operators = AffectedCatalogOperatorCollection()

    non_null_bundles = {
        (operator, bundle)
        for operator, bundles in all_affected_catalog_operators.items()
        for bundle in bundles
        if bundle is not None
    }

    affected_catalog_operators.added = {
        (catalog, operator_catalog)
        for catalog, operator_catalog in non_null_bundles
        if head_repo.has_catalog(catalog)
        and head_repo.catalog(catalog).has(operator_catalog)
        and not (
            base_repo.has_catalog(catalog)
            and base_repo.catalog(catalog).has(operator_catalog)
        )
    }

    affected_catalog_operators.modified = {
        (catalog, operator_catalog)
        for catalog, operator_catalog in non_null_bundles
        if head_repo.has_catalog(catalog)
        and base_repo.has_catalog(catalog)
        and head_repo.catalog(catalog).has(operator_catalog)
        and base_repo.catalog(catalog).has(operator_catalog)
    }

    affected_catalog_operators.deleted = {
        (catalog, operator_catalog)
        for catalog, operator_catalog in non_null_bundles
        if (not head_repo.has_catalog(catalog) and base_repo.has_catalog(catalog))
        or (
            not head_repo.catalog(catalog).has(operator_catalog)
            and base_repo.catalog(catalog).has(operator_catalog)
        )
    }
    LOGGER.debug("Affected catalog operators: %s", affected_catalog_operators)

    return affected_catalog_operators


def detect_changed_catalogs(
    head_repo: OperatorRepo,
    base_repo: OperatorRepo,
    all_affected_catalog_operators: dict[str, set[Optional[str]]],
) -> AffectedCatalogCollection:
    """
    Given two snapshots of an operator repository returns a dictionary
    of changed catalogs

    Args:
        head_repo (OperatorRepo): A snapshot of the operator repository after the changes
        base_repo (OperatorRepo): A snapshot of the operator repository before the changes
        all_affected_bundles (dict[str, set[Optional[str]]]): A dictionary mapping catalogs

    Returns:
        AffectedCatalogCollection: An object with added, modified and deleted
        catalogs
    """
    affected_catalogs = AffectedCatalogCollection()

    affected_catalogs.added = {
        catalog
        for catalog in all_affected_catalog_operators
        if head_repo.has_catalog(catalog) and not base_repo.has_catalog(catalog)
    }

    affected_catalogs.modified = {
        catalog
        for catalog in all_affected_catalog_operators
        if head_repo.has_catalog(catalog) and base_repo.has_catalog(catalog)
    }
    affected_catalogs.deleted = {
        catalog
        for catalog in all_affected_catalog_operators
        if not head_repo.has_catalog(catalog) and base_repo.has_catalog(catalog)
    }

    LOGGER.debug("Affected catalogs: %s", affected_catalogs)
    return affected_catalogs


def detect_changes(
    head_repo: OperatorRepo, base_repo: OperatorRepo, pr_url: str
) -> ParserResults:
    """
    Detect changes in the operator repository and return a dictionary containing
    categories of changes on catalog, operator, bundle and
    catalog operator level

    Args:
        head_repo (OperatorRepo): A snapshot of the operator repository after the changes
        base_repo (OperatorRepo): A snapshot of the operator repository before the changes
        pr_url (str): Pull request URL with the changes

    Returns:
        dict[str, list[str]]: Changes in the operator repository
    """
    pr_files = github_pr_affected_files(pr_url)
    (
        all_affected_bundles,
        all_affected_catalog_operators,
        non_operator_files,
    ) = _affected_bundles_and_operators_from_files(pr_files, head_repo, base_repo)

    operators = detect_changed_operators(head_repo, base_repo, all_affected_bundles)
    bundles = detect_changed_operator_bundles(
        head_repo, base_repo, all_affected_bundles
    )
    catalogs = detect_changed_catalogs(
        head_repo, base_repo, all_affected_catalog_operators
    )
    catalog_operators = detect_changed_catalog_operators(
        head_repo, base_repo, all_affected_catalog_operators
    )

    parsed_results = ParserResults(
        affected_operators=operators,
        affected_bundles=bundles,
        affected_catalogs=catalogs,
        affected_catalog_operators=catalog_operators,
        extra_files=non_operator_files,
    )

    return parsed_results


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
    head_repo = OperatorRepo(args.repo_path)
    base_repo = OperatorRepo(args.base_repo_path)

    result = detect_changes(head_repo, base_repo, args.pr_url)

    # raise exception if the result is invalid
    ParserRules(result, head_repo, base_repo).validate()

    if args.output_file:
        with args.output_file.open(mode="w", encoding="utf-8") as output_file:
            json.dump(result.to_dict(), output_file)
    else:
        print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
