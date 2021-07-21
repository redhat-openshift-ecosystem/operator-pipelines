import json
import pathlib
from urllib.parse import urljoin
from typing import Any, Dict, List, Tuple

import requests
import yaml


# Bundle annotations
OCP_VERSIONS_ANNOTATION = "com.redhat.openshift.versions"
PACKAGE_ANNOTATION = "operators.operatorframework.io.bundle.package.v1"

# ClusterServiceVersion annotations & properties
OLM_PROPS_ANNOTATION = "olm.properties"
MAX_OCP_VERSION_PROPERTY = "olm.maxOpenShiftVersion"


def find_file(base_path, relative_paths: List[Tuple[str]]) -> pathlib.Path:
    """
    Finds the first file that exists in a list of relative paths.

    Args:
        base_path (Path): A root path to start from
        relative_paths (List[Tuple[str]]): An ordered list of relative paths
            (in tuples) to look for.

    Returns:
        A Path object for the first file found; None otherwise.
    """
    for path in relative_paths:
        new_path = base_path.joinpath(*path)
        if new_path.exists() and new_path.is_file():
            return new_path
    return None


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
        args: Parsed args from ArgumentParser

    Returns:
        A dict of pertinent OCP version information
    """
    bundle_annotations = get_bundle_annotations(bundle_path)

    ocp_versions_range = str(bundle_annotations.get(OCP_VERSIONS_ANNOTATION))
    if not ocp_versions_range:
        raise ValueError(
            f"'{OCP_VERSIONS_ANNOTATION}' annotation not defined"
        )  # pragma: no cover

    package = bundle_annotations.get(PACKAGE_ANNOTATION)
    if not package:
        raise ValueError(
            f"'{PACKAGE_ANNOTATION}' annotation not defined"
        )  # pragma: no cover

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
