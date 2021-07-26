import json
import logging
import pathlib
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Tuple

import requests
import yaml

from operatorcert.utils import find_file, str_color

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


def get_csv_annotations(bundle_path: pathlib.Path, package: str) -> Dict:
    """
    Gets all the annotations from the bundle CSV

    Args:
        bundle_path (Path): A path to the bundle version
        package (str): Operator package name

    Returns:
        A dict of all the annotation keys and values
    """
    paths = [
        ("manifests", f"{package}.clusterserviceversion.yaml"),
        ("manifests", f"{package}.clusterserviceversion.yml"),
    ]
    csv_path = find_file(bundle_path, paths)
    if not csv_path:
        raise RuntimeError("Cluster service version (CSV) file not found")

    with csv_path.open() as fh:
        content = yaml.safe_load(fh)
        return content.get("metadata", {}).get("annotations", {})


def get_supported_indices(
    pyxis_url: str, ocp_versions_range: str, max_ocp_version: str = None
) -> List[str]:
    """
    Gets all the known supported OCP indices for this bundle.

    Args:
        pyxis_url (str): Base URL to Pyxis
        ocp_versions_range (str): OpenShift version annotation
        max_ocp_version (str): OLM property in the bundle CSV

    Returns:
        A list of supported OCP versions in descending order
    """
    url = urljoin(pyxis_url, "v1/operators/indices")

    filter_ = f"organization==certified-operators"
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


def ocp_version_info(bundle_path: pathlib.Path, pyxis_url: str) -> Dict:
    """
    Gathers some information pertaining to the OpenShift versions defined in the
    Operator bundle.

    Args:
        bundle_path (Path): A path to the root of the bundle
        pyxis_url (str): Base URL to Pyxis

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
        pyxis_url, ocp_versions_range, max_ocp_version=max_ocp_version
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
    parsed = urlparse(git_repo_url)
    path = parsed.path.rstrip(".git")
    path_components = path.split("/")
    if len(path_components) != 3:
        raise ValueError(
            f"{git_repo_url} is not a valid repository link. "
            f"Valid link should look like "
            f"'https://github.com/redhat-openshift-ecosystem/operator-pipelines'"
        )
    repository = path_components[-1]
    organization = path_components[-2]

    return organization, repository


def get_files_changed_in_pr(
    organization: str, repository: str, base_branch: str, pr_head_label: str
) -> List[str]:
    """
    Get the list of files modified in the PR against the base branch.
    """
    compare_changes_url = (
        f"https://api.github.com/repos/{organization}/{repository}"
        f"/compare/{base_branch}...{pr_head_label}"
    )
    pr_data = requests.get(compare_changes_url).json()

    filenames = []
    for file in pr_data.get("files", []):
        filenames.append(file["filename"])

    return filenames


def verify_changed_files_location(
    changed_files: List[str], repository: str, operator_name: str, operator_version: str
) -> None:
    """
    Find the allowed locations in directory tree for changes
    (basing on the operator name and version).
    Test if all of the changes are in allowed locations.
    """

    path = f"{repository}/operators/{operator_name}/" + operator_version

    logging.info(
        str_color(
            "blue",
            f"Changes for operator {operator_name} in version {operator_version}"
            f" are expected to be in path: \n"
            f" -{path}/* \n",
        )
    )

    wrong_changes = False
    for file_path in changed_files:
        if file_path.startswith(path):
            logging.info(str_color("green", f"Change path ok: {file_path}"))
            continue
        else:
            logging.error(str_color("red", f"Wrong change path: {file_path}"))
            wrong_changes = True

    if wrong_changes:
        raise RuntimeError("There are changes in the invalid path")
