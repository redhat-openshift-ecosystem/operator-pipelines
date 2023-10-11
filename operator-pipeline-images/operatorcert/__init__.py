"""
Main module for the operator certification tool
"""
import json
import logging
import pathlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional
from urllib.parse import urljoin

import yaml
from dateutil.parser import isoparse
from operatorcert import github, pyxis
from operatorcert.utils import find_file

# Bundle annotations
OCP_VERSIONS_ANNOTATION = "com.redhat.openshift.versions"
PACKAGE_ANNOTATION = "operators.operatorframework.io.bundle.package.v1"

LOGGER = logging.getLogger("operator-cert")


def get_bundle_annotations(bundle_path: pathlib.Path) -> Dict[str, Any]:
    """
    Gets all the annotations from the bundle metadata

    Args:
        bundle_path (Path): A path to the bundle version

    Returns:
        A dict of all the annotation keys and values
    """
    paths = [
        ("metadata", "annotations.yaml"),
        ("metadata", "annotations.yml"),
    ]
    annotations_path = find_file(bundle_path, paths)  # type: ignore
    if not annotations_path:
        raise RuntimeError("Annotations file not found")

    with annotations_path.open() as annotation_file:
        content = yaml.safe_load(annotation_file)
        return content.get("annotations") or {}


def get_csv_content(bundle_path: pathlib.Path, package: str) -> Any:
    """
    Gets all the content of the bundle CSV

    Args:
        bundle_path (Path): A path to the bundle version
        package (str): Operator package name

    Returns:
        A dict of all the fields in the bundle CSV
    """
    paths = [
        ("manifests", f"{package}.clusterserviceversion.yaml"),
        ("manifests", f"{package}.clusterserviceversion.yml"),
    ]
    csv_path = find_file(bundle_path, paths)  # type: ignore
    if not csv_path:
        raise RuntimeError("Cluster service version (CSV) file not found")

    with csv_path.open() as csv_file:
        return yaml.safe_load(csv_file)


def get_supported_indices(
    pyxis_url: str,
    ocp_versions_range: Any,
    organization: str,
) -> List[Dict[str, Any]]:
    """
    Gets all the known supported OCP indices for this bundle.

    Args:
        pyxis_url (str): Base URL to Pyxis
        ocp_versions_range (str): OpenShift version annotation
        organization (str): Organization of the index (e.g. "certified-operators")

    Returns:
        A list of supported OCP versions in descending order
    """
    url = urljoin(pyxis_url, "v1/operators/indices")

    filter_ = f"organization=={organization}"

    # Ignoring pagination. 500 OCP versions would be a lot for a single
    # version of an operator to support.
    params = {
        "filter": filter_,
        "page_size": 500,
        "sort_by": "ocp_version[desc]",
        "include": "data.ocp_version,data.path,data.end_of_life",
    }
    if ocp_versions_range:
        params["ocp_versions_range"] = ocp_versions_range

    rsp = pyxis.get(url, params=params, auth_required=False)
    rsp.raise_for_status()
    return rsp.json().get("data") or []


def filter_out_eol_versions(indices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters out indices that have reached their end of life.

    Args:
        indices (List[Dict]): List of operator indices

    Returns:
        List[Dict]: List of operator indices that have not reached their end of life
    """
    supported_indices = []
    now = datetime.now(timezone.utc)
    for index in indices:
        eol = index.get("end_of_life")
        if eol:
            eol_datetime = isoparse(eol).astimezone(timezone.utc)
            if eol_datetime <= now:
                LOGGER.warning(
                    "OpenShift %s has reached its end of life", index["ocp_version"]
                )
                continue
        supported_indices.append(index)

    return supported_indices


def get_skipped_versions(
    all_indices: List[Dict[str, Any]], supported_indices: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Compares the list of all indices to the list of supported indices and
    returns a diff with a list of not supported indices.

    Args:
        all_indices (List[Dict]): List of all indices
        supported_indices (List[Dict]): List of supported indices

    Returns:
        List[Dict]: List of not supported indices
    """
    supported_versions = [index["ocp_version"] for index in supported_indices]
    all_versions = [index["ocp_version"] for index in all_indices]
    skipped_versions = list(set(all_versions) - set(supported_versions))

    skipped_indices = []
    for version in all_indices:
        if version["ocp_version"] in skipped_versions:
            skipped_indices.append(version)

    return skipped_indices


def ocp_version_info(
    bundle_path: Optional[pathlib.Path], pyxis_url: str, organization: str
) -> Dict[str, Any]:
    """
    Gathers some information pertaining to the OpenShift versions defined in the
    Operator bundle. If bundle_path is None, retrieve information about all
    currently supported OpenShift versions.

    Args:
        bundle_path (Path): A path to the root of the bundle
        pyxis_url (str): Base URL to Pyxis
        organization (str): Organization of the index (e.g. "certified-operators")

    Returns:
        A dict of pertinent OCP version information
    """
    if bundle_path is None:
        ocp_versions_range: Any = None
    else:
        bundle_annotations = get_bundle_annotations(bundle_path)

        ocp_versions_range = bundle_annotations.get(OCP_VERSIONS_ANNOTATION)
        if not ocp_versions_range and organization != "community-operators":
            # Community operators are not required to have this annotation
            raise ValueError(f"'{OCP_VERSIONS_ANNOTATION}' annotation not defined")

        package = bundle_annotations.get(PACKAGE_ANNOTATION)
        if not package:
            raise ValueError(f"'{PACKAGE_ANNOTATION}' annotation not defined")

    indices = get_supported_indices(pyxis_url, ocp_versions_range, organization)
    supported_indices = filter_out_eol_versions(indices)

    if not supported_indices:
        raise ValueError("No supported indices found")

    # Now get all available indices without using version range
    all_indices = supported_indices
    if ocp_versions_range:
        # We need to get all indices to determine which ones are not supported
        all_indices = get_supported_indices(pyxis_url, None, organization)
        all_indices = filter_out_eol_versions(all_indices)

    return {
        "versions_annotation": ocp_versions_range,
        "indices": supported_indices,
        "max_version_index": supported_indices[0],
        "all_indices": all_indices,
        "not_supported_indices": get_skipped_versions(all_indices, supported_indices),
    }


def get_repo_and_org_from_github_url(git_repo_url: str) -> Tuple[str, str]:
    """
    Parse github repository URL to get the organization (or user) and
    repository name
    """

    wrong_path_err = (
        f"{git_repo_url} is not a valid repository link. "
        f"Valid link should either look like "
        f"'git@github.com:redhat-openshift-ecosystem/operator-pipelines.git' or "
        f"'https://github.com/redhat-openshift-ecosystem/operator-pipelines.git'"
    )

    # ssh path
    if git_repo_url.startswith("git@github.com:") and git_repo_url.endswith(".git"):
        path = git_repo_url.removeprefix("git@github.com:").removesuffix(".git")
    # https path
    elif git_repo_url.startswith("https://github.com/") and git_repo_url.endswith(
        ".git"
    ):
        path = git_repo_url.removeprefix("https://github.com/").removesuffix(".git")
    else:
        raise ValueError(wrong_path_err)

    path_components = path.split("/")
    if len(path_components) != 2:
        raise ValueError(wrong_path_err)
    organization = path_components[0]
    repository = path_components[1]

    return organization, repository


def get_files_added_in_pr(
    organization: str, repository: str, base_branch: str, pr_head_label: str
) -> List[str]:
    """
    Get the list of files added in the PR.
    Raise error if any existing files are changed
    """
    compare_changes_url = (
        f"https://api.github.com/repos/{organization}/{repository}"
        f"/compare/{base_branch}...{pr_head_label}"
    )
    comparison = github.get(compare_changes_url, auth_required=False)

    added_files = []
    modified_files = []
    allowed_files = []

    for file in comparison.get("files", []):
        if file["status"] == "added":
            added_files.append(file["filename"])
        else:
            # To prevent the modifications to previously merged bundles,
            # we allow only changed with status "added"
            modified_files.append(file)

    allowed_files.extend(added_files)

    if modified_files:
        for modified_file in modified_files:
            if not modified_file["filename"].endswith("ci.yaml"):
                LOGGER.error(
                    "Change not permitted: file: %s, status: %s",
                    modified_file["filename"],
                    modified_file["status"],
                )
                raise RuntimeError("There are changes done to previously merged files")
            allowed_files.append(modified_file["filename"])

    return allowed_files


def verify_changed_files_location(
    changed_files: List[str], operator_name: str, bundle_version: str
) -> None:
    """
    Find the allowed locations in directory tree for changes
    (basing on the operator name and version).
    Test if all of the changes are in allowed locations.
    """
    parent_path = f"operators/{operator_name}"
    path = parent_path + "/" + bundle_version
    config_path = parent_path + "/ci.yaml"

    LOGGER.info(
        "Changes for operator %s in version %s"
        " are expected to be in paths: \n"
        " %s/* \n"
        " %s",
        operator_name,
        bundle_version,
        path,
        config_path,
    )

    wrong_changes = False
    for file_path in changed_files:
        if file_path.startswith(path) or file_path == config_path:
            LOGGER.info("Permitted change: %s ", file_path)
        else:
            LOGGER.error("Unpermitted change: %s", file_path)
            wrong_changes = True

    if wrong_changes:
        raise RuntimeError("There are unpermitted file changes")


def parse_pr_title(pr_title: str) -> Tuple[str, str]:
    """
    Test, if PR title complies to regex.
    If yes, extract the Bundle name and version.
    """
    # Verify if PR title follows convention- it should contain the bundle name and version.
    # Any non- empty string without whitespaces makes a valid version.
    regex = r"^operator ([a-zA-Z0-9-]+) \(([^\s]+)\)$"
    regex_pattern = re.compile(regex)

    matching = regex_pattern.search(pr_title)
    if not matching:
        raise ValueError(
            f"Pull request title {pr_title} does not follow the regex "
            "'operator <operator_name> (<version>)"
        )

    bundle_name = matching.group(1)
    bundle_version = matching.group(2)

    return bundle_name, bundle_version


def validate_user(git_username: str, contacts: List[str]) -> None:
    """
    Check if git username is in the allowed list of contacts

    Args:
        git_username (str): Git username
        contacts (List[str]): List of allowed contacts

    """
    if git_username not in contacts:
        raise ValueError(
            f"User {git_username} doesn't have permissions to submit the bundle."
        )
    LOGGER.info("User %s has permission to submit the bundle.", git_username)


def verify_pr_uniqueness(
    available_repositories: List[str], base_pr_url: str, base_pr_bundle_name: str
) -> None:
    """
    List the active Pull Requests in given GitHub repositories.
    Find Pull Requests for the same Operator Bundle, and error if they exists.
    """

    base_url = "https://api.github.com/repos/"

    regex = r"^operator ([a-zA-Z0-9-]+) [^\s]+$"
    regex_pattern = re.compile(regex)

    for repo in available_repositories:
        # List the open PRs in the given repositories,
        pull_requests = github.get(base_url + repo + "/pulls", auth_required=False)

        # find duplicates
        duplicate_prs = []
        for pull_request in pull_requests:
            pr_title = pull_request["title"]
            pr_url = pull_request["html_url"]
            if base_pr_url == pr_url:
                # We found the base PR
                continue
            matching = regex_pattern.search(pr_title)
            # there is a PR with name that doesn't conform to regex
            if matching is None:
                continue
            bundle_name = matching.group(1)
            if bundle_name == base_pr_bundle_name:
                duplicate_prs.append(f"{pr_title}: {pr_url}")

        # Log duplicates and exit with error
        if duplicate_prs:
            LOGGER.error(
                "There is more than one pull request for the Operator Bundle %s",
                base_pr_bundle_name,
            )
            for duplicate in duplicate_prs:
                LOGGER.error("DUPLICATE: %s", duplicate)
            raise RuntimeError("Multiple pull requests for one Operator Bundle")


def download_test_results(args: Any) -> Any:
    """
    Try to get the test results for given parameters from the Pyxis.
    On success, store the results in file and return it's id, on failure- return None.
    """

    # If there are multiple results, we only want the most recent one- we enforce
    # it by sorting by creation_date
    # and getting only the first result.
    test_results_url = urljoin(
        args.pyxis_url,
        f"v1/projects/certification/id/{args.cert_project_id}/test-results?"
        f"filter=certification_hash=='{args.certification_hash}';"
        f"version=='{args.operator_package_version}';"
        f"operator_package_name=='{args.operator_name}'"
        f"&sort_by=creation_date[desc]&page_size=1",
    )

    rsp = pyxis.get(test_results_url)

    rsp.raise_for_status()
    query_results = rsp.json()["data"]

    if len(query_results) == 0:
        LOGGER.error("There is no test results for given parameters")
        return None

    # Get needed data from the query result
    # test results
    result = json.dumps(
        {
            "passed": query_results[0]["passed"],
            "results": query_results[0]["results"],
            "test_library": query_results[0]["test_library"],
        },
        indent=4,
    )
    file_path = "test_results.json"

    # Save needed data
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(result)

    LOGGER.info("Test results retrieved successfully for given parameters")
    return query_results[0]["_id"]
