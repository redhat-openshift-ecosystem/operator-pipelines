import logging
import os
from typing import Any, Dict
from urllib.parse import urljoin

import requests

LOGGER = logging.getLogger("operator-cert")


def is_internal() -> bool:
    """
    Check if provided configuration points to internal vs external Pyxis instance

    Returns:
        bool: Is internal Pyxis instance
    """
    cert = os.environ.get("PYXIS_CERT_PATH")
    key = os.environ.get("PYXIS_KEY_PATH")
    return cert and key


def _get_session(pyxis_url: str) -> requests.Session:
    """
    Create a Pyxis http session with auth based on env variables.

    Auth is set to use either API key or certificate + key.

    Args:
        url (str): Pyxis API URL

    Raises:
        Exception: Exception is raised when auth ENV variables are missing.

    Returns:
        requests.Session: Pyxis session
    """
    api_key = os.environ.get("PYXIS_API_KEY")
    cert = os.environ.get("PYXIS_CERT_PATH")
    key = os.environ.get("PYXIS_KEY_PATH")

    # Document about the proxy configuration:
    # https://source.redhat.com/groups/public/customer-platform-devops/digital_experience_operations_dxp_ops_wiki/using_squid_proxy_to_access_akamai_preprod_domains_over_vpn
    proxies = {}
    # If it is external preprod
    is_preprod = any(env in pyxis_url for env in ["dev", "qa", "stage"])
    if is_preprod and api_key:
        proxies = {
            "http": "http://squid.corp.redhat.com:3128",
            "https": "http://squid.corp.redhat.com:3128",
        }

    session = requests.Session()

    if api_key:
        LOGGER.debug("Pyxis session using API key is created")
        session.headers.update({"X-API-KEY": api_key})
    elif cert and key:
        if os.path.exists(cert) and os.path.exists(key):
            LOGGER.debug("Pyxis session using cert + key is created")
            session.cert = (cert, key)
        else:
            raise Exception(
                "PYXIS_CERT_PATH or PYXIS_KEY_PATH does not point to a file that "
                "exists."
            )
    else:
        # API key or cert + key need to be provided using env variable
        raise Exception(
            "No auth details provided for Pyxis. "
            "Either define PYXIS_API_KEY or PYXIS_CERT_PATH + PYXIS_KEY_PATH"
        )

    if proxies:
        LOGGER.debug(
            "Pyxis session configured for Proxy (external preprod environment)"
        )
        session.proxies.update(proxies)

    return session


def post(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST pyxis API request to given URL with given payload

    Args:
        url (str): Pyxis API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Dict[str, Any]: Pyxis response
    """
    session = _get_session(url)

    LOGGER.debug(f"POST Pyxis request: {url}")
    resp = session.post(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Pyxis POST query failed with {url} - {resp.status_code} - {resp.text}"
        )
        raise
    return resp.json()


def put(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    PUT pyxis API request to given URL with given payload

    Args:
        url (str): Pyxis API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Dict[str, Any]: Pyxis response
    """
    session = _get_session(url)

    LOGGER.debug(f"PATCH Pyxis request: {url}")
    resp = session.put(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Pyxis PUT query failed with {url} - {resp.status_code} - {resp.text}"
        )
        raise
    return resp.json()


def patch(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    PATCH pyxis API request to given URL with given payload

    Args:
        url (str): Pyxis API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Dict[str, Any]: Pyxis response
    """
    session = _get_session(url)

    LOGGER.debug(f"PATCH Pyxis request: {url}")
    resp = session.patch(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Pyxis PATCH query failed with {url} - {resp.status_code} - {resp.text}"
        )
        raise
    return resp.json()


def get(url: str) -> Any:
    """
    Pyxis GET request

    Args:
        url (str): Pyxis URL

    Returns:
        Any: Pyxis GET request response
    """
    session = _get_session(url)
    LOGGER.debug(f"GET Pyxis request: {url}")
    resp = session.get(url)
    # Not raising exception for error statuses, because GET request can be used to check
    # if something exists. We don't want a 404 to cause failures.

    return resp


def get_project(base_url: str, project_id: str) -> Dict[str, Any]:
    """
    Get project details for given project ID

    Args:
        base_url (str): Pyxis base URL
        project_id (str): certification project ID

    Returns:
        Dict[str, Any]: Pyxis project response
    """
    session = _get_session(base_url)

    project_url = urljoin(base_url, f"v1/projects/certification/id/{project_id}")
    LOGGER.debug(f"Getting project details: {project_id}")
    resp = session.get(project_url)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Unable to get project details {project_url} - {resp.status_code} - {resp.text}"
        )
        raise
    return resp.json()


def get_vendor_by_org_id(base_url: str, org_id: str) -> Dict[str, Any]:
    """
    Get vendor using organization ID

    Args:
        base_url (str): Pyxis based API url
        org_id (str): Organization ID

    Returns:
        Dict[str, Any]: Vendor Pyxis response
    """
    session = _get_session(base_url)

    project_url = urljoin(base_url, f"v1/vendors/org-id/{org_id}")
    LOGGER.debug(f"Getting project details by org_id: {org_id}")
    resp = session.get(project_url)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Unable to get vendor details {project_url} - {resp.status_code} - {resp.text}"
        )
        raise
    return resp.json()


def get_repository_by_isv_pid(base_url: str, isv_pid: str) -> Dict[str, Any]:
    """
    Get container repository using ISV pid

    Args:
        base_url (str): Pyxis based API url
        isv_pid (str): Project's isv_pid

    Returns:
        Dict[str, Any]: Repository Pyxis response
    """
    session = _get_session(base_url)

    repo_url = urljoin(base_url, "v1/repositories")
    LOGGER.debug(f"Getting repository details by isv_pid: {isv_pid}")
    query_filter = f"isv_pid=={isv_pid}"
    resp = session.get(repo_url, params={"filter": query_filter})

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Unable to get vendor details {repo_url} - {resp.status_code} - {resp.text}"
        )
        raise
    json_resp = resp.json()
    return None if len(json_resp.get("data")) == 0 else json_resp["data"][0]
