import json
import logging
import pathlib
import re
from urllib.parse import urljoin
from typing import Dict, List, Optional

import requests
import yaml

from operatorcert import pyxis
from operatorcert.utils import find_file, store_results

# Bundle annotations
OCP_VERSIONS_ANNOTATION = "com.redhat.openshift.versions"
PACKAGE_ANNOTATION = "operators.operatorframework.io.bundle.package.v1"

# ClusterServiceVersion annotations & properties
OLM_PROPS_ANNOTATION = "olm.properties"
MAX_OCP_VERSION_PROPERTY = "olm.maxOpenShiftVersion"


def get_bundle_annotations(bundle_path: pathlib.Path) -> Dict:
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
    annotations_path = find_file(bundle_path, paths)
    if not annotations_path:
        raise RuntimeError("Annotations file not found")

    with annotations_path.open() as fh:
        content = yaml.safe_load(fh)
        return content.get("annotations", {})


def get_csv_content(bundle_path: pathlib.Path, package: str) -> Dict:
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
    csv_path = find_file(bundle_path, paths)
    if not csv_path:
        raise RuntimeError("Cluster service version (CSV) file not found")

    with csv_path.open() as fh:
        return yaml.safe_load(fh)


def get_csv_annotations(bundle_path: pathlib.Path, package: str) -> Dict:
    """
    Gets all the annotations from the bundle CSV

    Args:
        bundle_path (Path): A path to the bundle version
        package (str): Operator package name

    Returns:
        A dict of all the annotation keys and values
    """
    content = get_csv_content(bundle_path, package)
    return content.get("metadata", {}).get("annotations", {})


def get_supported_indices(
    pyxis_url: str,
    ocp_versions_range: str,
    organization: str,
    max_ocp_version: str = None,
) -> List[str]:
    """
    Gets all the known supported OCP indices for this bundle.

    Args:
        pyxis_url (str): Base URL to Pyxis
        ocp_versions_range (str): OpenShift version annotation
        organization (str): Organization of the index (e.g. "certified-operators")
        max_ocp_version (str): OLM property in the bundle CSV

    Returns:
        A list of supported OCP versions in descending order
    """
    url = urljoin(pyxis_url, "v1/operators/indices")

    filter_ = f"organization=={organization}"
    if max_ocp_version:
        filter_ += f";ocp_version=le={max_ocp_version}"

    # Ignoring pagination. 500 OCP versions would be a lot for a single
    # version of an operator to support.
    params = {
        "filter": filter_,
        "ocp_versions_range": ocp_versions_range,
        "page_size": 500,
        "sort_by": "ocp_version[desc]",
        "include": "data.ocp_version,data.path",
    }

    rsp = requests.get(url, params=params)
    rsp.raise_for_status()
    return rsp.json()["data"]


def ocp_version_info(
    bundle_path: pathlib.Path, pyxis_url: str, organization: str
) -> Dict:
    """
    Gathers some information pertaining to the OpenShift versions defined in the
    Operator bundle.

    Args:
        bundle_path (Path): A path to the root of the bundle
        pyxis_url (str): Base URL to Pyxis
        organization (str): Organization of the index (e.g. "certified-operators")

    Returns:
        A dict of pertinent OCP version information
    """
    bundle_annotations = get_bundle_annotations(bundle_path)

    ocp_versions_range = bundle_annotations.get(OCP_VERSIONS_ANNOTATION)
    if not ocp_versions_range:
        raise ValueError(f"'{OCP_VERSIONS_ANNOTATION}' annotation not defined")

    package = bundle_annotations.get(PACKAGE_ANNOTATION)
    if not package:
        raise ValueError(f"'{PACKAGE_ANNOTATION}' annotation not defined")

    csv_annotations = get_csv_annotations(bundle_path, package)

    olm_props_content = csv_annotations.get(OLM_PROPS_ANNOTATION, "[]")
    olm_props = json.loads(olm_props_content)

    max_ocp_version = None
    for prop in olm_props:
        if prop.get("type") == MAX_OCP_VERSION_PROPERTY:
            max_ocp_version = str(prop["value"])
            break

    indices = get_supported_indices(
        pyxis_url, ocp_versions_range, organization, max_ocp_version=max_ocp_version
    )

    if not indices:
        raise ValueError("No supported indices found")

    return {
        "versions_annotation": ocp_versions_range,
        "max_version_property": max_ocp_version,
        "indices": indices,
        "max_version_index": indices[0],
    }


def get_repo_and_org_from_github_url(git_repo_url: str) -> (str, str):
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
    rsp = requests.get(compare_changes_url)
    rsp.raise_for_status()

    added_files_names = []
    modified_files = []
    for file in rsp.json().get("files", []):
        if file["status"] == "added":
            added_files_names.append(file["filename"])
        else:
            # To prevent the modifications to previously merged bundles,
            # we allow only changed with status "added"
            modified_files.append(file)

    if modified_files:
        for modified_file in modified_files:
            logging.error(
                f"Change not permitted: file: {modified_file['filename']}, status: {modified_file['status']}"
            )
        raise RuntimeError("There are changes done to previously merged files")

    return added_files_names


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

    logging.info(
        f"Changes for operator {operator_name} in version {bundle_version}"
        f" are expected to be in paths: \n"
        f" {path}/* \n"
        f" {config_path}"
    )

    wrong_changes = False
    for file_path in changed_files:
        if file_path.startswith(path) or file_path == config_path:
            logging.info(f"Change path ok: {file_path}")
        else:
            logging.error(f"Wrong change path: {file_path}")
            wrong_changes = True

    if wrong_changes:
        raise RuntimeError("There are changes in the invalid path")


def parse_pr_title(pr_title: str) -> (str, str):
    """
    Test, if PR title complies to regex.
    If yes, extract the Bundle name and version.
    """
    # Verify if PR title follows convention- it should contain the bundle name and version.
    # Any non- empty string without whitespaces makes a valid version.
    regex = rf"^operator ([a-zA-Z0-9-]+) \(([^\s]+)\)$"
    regex_pattern = re.compile(regex)

    if not regex_pattern.match(pr_title):
        raise ValueError(
            f"Pull request title {pr_title} does not follow the regex 'operator <operator_name> (<version>)"
        )

    matching = regex_pattern.search(pr_title)
    bundle_name = matching.group(1)
    bundle_version = matching.group(2)

    return bundle_name, bundle_version


def validate_user(git_username: str, contacts: List[str]):
    if git_username not in contacts:
        raise Exception(
            f"User {git_username} doesn't have permissions to submit the bundle."
        )
    else:
        logging.info(f"User {git_username} has permission to submit the bundle.")


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
        rsp = requests.get(base_url + repo + "/pulls")
        rsp.raise_for_status()
        prs = rsp.json()

        # find duplicates
        duplicate_prs = []
        for pr in prs:
            pr_title = pr["title"]
            pr_url = pr["html_url"]
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
            logging.error(
                f"There is more than one pull request for the Operator Bundle {base_pr_bundle_name}"
            )
            for duplicate in duplicate_prs:
                logging.error(f"DUPLICATE: {duplicate}")
            raise RuntimeError("Multiple pull requests for one Operator Bundle")


def download_test_results(args) -> Optional[str]:
    """
    Try to get the test results for given parameters from the Pyxis.
    On success, store the results in file and return it's id, on failure- return None.
    """

    # If there are multiple results, we only want the most recent one- we enforce it by sorting by creation_date
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
        logging.error(f"There is no test results for given parameters")
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
    with open(file_path, "w") as file:
        file.write(result)

    logging.info(f"Test results retrieved successfully for given parameters")
    return query_results[0]["_id"]
