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
