"""Utility functions for operator certification."""

import argparse
import json
import logging
import os
import pathlib
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from packaging.version import Version

LOGGER = logging.getLogger("operator-cert")


def find_file(
    base_path: pathlib.Path, relative_paths: List[Tuple[str, ...]]
) -> Optional[pathlib.Path]:
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


def store_results(results: Dict[str, Any]) -> None:
    """
    Store the given results into files in given directory.

    Args:
        results (Dict): Dictionary, where key is a result name (name of file to store value),
        and value is result value (to be stored in file).
    """
    for result_name, result_value in results.items():
        if result_value is None:
            result_value = ""
            LOGGER.error("Result %s is empty", result_name)
        LOGGER.debug("Storing %s", result_name)
        with open(result_name, "w", encoding="utf-8") as result_file:
            if isinstance(result_value, dict):
                json.dump(result_value, result_file)
            else:
                result_file.write(str(result_value))


def set_client_keytab(keytab_file: str) -> None:
    """
    Set env variable with default client keytab.
    Args:
        keytab_file (path): path to keytab file (default /etc/krb5.krb)
    """
    if not keytab_file:
        return
    if not os.path.isfile(keytab_file):
        raise IOError(f"Keytab file {keytab_file} does not exist")
    os.environ["KRB5_CLIENT_KTNAME"] = f"FILE:{keytab_file}"
    LOGGER.debug(
        "Set KRB5_CLIENT_KTNAME env variable: %s", os.environ["KRB5_CLIENT_KTNAME"]
    )


def add_session_retries(
    session: Session,
    total: int = 10,
    backoff_factor: float = 1,
    status_forcelist: Optional[Tuple[int, ...]] = (408, 500, 502, 503, 504),
) -> None:
    """
    Adds retries to a requests HTTP/HTTPS session.
    The default values provide exponential backoff for a max wait of ~8.5 mins

    Reference the urllib3 documentation for more details about the kwargs.

    Args:
        session (Session): A requests session
        total (int): See urllib3 docs
        backoff_factor (int): See urllib3 docs
        status_forcelist (tuple[int]|None): See urllib3 docs
    """
    retries = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        # Don't raise a MaxRetryError for codes in status_forcelist.
        # This allows for more graceful exception handling using
        # Response.raise_for_status.
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)


def get_repo_config(repo_config_file: str) -> Any:
    """
    Read repository configuration file.

    Args:
        repo_config_file (str): Path to repository configuration file

    Returns:
        Any: A dictionary with repository configuration
    """
    with open(repo_config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class SplitArgs(argparse.Action):
    """
    Split comma separated list of arguments into a list
    """

    def __call__(
        self, parser: Any, namespace: Any, values: Any, option_string: Any = None
    ) -> None:
        setattr(namespace, self.dest, values.split(","))


def run_command(
    cmd: List[str], check: bool = True, cwd: Optional[str] = None
) -> subprocess.CompletedProcess[bytes]:
    """
    Run a shell command and return its output.

    Args:
        cmd (List[str]): Command to run

    Returns:
        CompletedProcess: Command output
    """
    LOGGER.debug("Running command: %s", cmd)
    try:
        output = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
            cwd=cwd,
        )
    except subprocess.CalledProcessError as e:
        LOGGER.error(
            "Error running command: \nstdout: %s\nstderr: %s",
            e.stdout,
            e.stderr,
        )
        raise e
    LOGGER.debug("Command output: %s", output.stdout.decode("utf-8"))
    return output


def get_ocp_supported_versions(organization: str, ocp_metadata_version: Any) -> Any:
    """
    This function translates ocp version range to the supported OCP versions
    using Pyxis indices API.

    Args:
        organization (str): Organization of the index (e.g. "certified-operators")
        ocp_metadata_version (Any): OCP version annotation in the CSV

    Returns:
        Any: List of supported OCP versions for the given range and organization
    """
    indices_url = "https://catalog.redhat.com/api/containers/v1/operators/indices"
    params = {
        "filter": f"organization=={organization}",
        "sort_by": "ocp_version[desc]",
        "include": "data.ocp_version",
    }
    if ocp_metadata_version:
        params["ocp_versions_range"] = ocp_metadata_version

    rsp = requests.get(indices_url, params=params, timeout=60)
    try:
        rsp.raise_for_status()
    except requests.HTTPError as exc:
        LOGGER.error("GET request to fetch the indices failed with: %s", exc)
        return None

    indices = rsp.json().get("data")
    return [index.get("ocp_version") for index in indices]


def copy_images_to_destination(
    iib_responses: Any,
    destination: str,
    tag_suffix: str,
    auth_file: Optional[str] = None,
) -> None:
    """
    Copy IIB index images to a destination given by parameter

    Args:
        iib_response (Any): IIB build response object
        destination (str): Registry and repository destination for the index images
        tag_suffix (str): Tag suffix to append to the index image
        auth_file (Optional[str], optional): Auth file for destination registry.
        Defaults to None.
    """
    for response in iib_responses:
        version = response.get("from_index", "").split(":")[-1]
        cmd = [
            "skopeo",
            "copy",
            "--retry-times",
            "5",
            f"docker://{response.get('index_image_resolved')}",
            f"docker://{destination}:{version}{tag_suffix}",
        ]
        if auth_file:
            cmd.extend(["--authfile", auth_file])

        LOGGER.info("Copying image to destination: %s", cmd)
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def sort_versions(version_list: list[Any]) -> list[Any]:
    """
    Returns a sorted list of version strings in ascending order.
    Example of the input: ["v4.12", "v4.11", "v4.9"]

    The sorting is done by version number, not by string comparison.

    Args:
        version_list (list[Any]): A list of version strings to be sorted.

    Returns:
        list[Any]: A sorted list of version strings.
    """
    return sorted(version_list, key=lambda x: Version(x[1:]))
