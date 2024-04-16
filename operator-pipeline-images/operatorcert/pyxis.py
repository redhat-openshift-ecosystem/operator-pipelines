"""Pyxis API client"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from operatorcert.utils import add_session_retries

LOGGER = logging.getLogger("operator-cert")


def is_internal() -> bool:
    """
    Check if provided configuration points to internal vs external Pyxis instance

    Returns:
        bool: Is internal Pyxis instance
    """
    cert = os.environ.get("PYXIS_CERT_PATH")
    key = os.environ.get("PYXIS_KEY_PATH")
    return bool(cert and key)


def _get_session(pyxis_url: str, auth_required: bool = True) -> requests.Session:
    """
    Create a Pyxis http session with auth based on env variables.

    Auth is optional and can be set to use either API key or certificate + key.

    Args:
        url (str): Pyxis API URL
        auth_required (bool): Whether authentication should be required for the session

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
    add_session_retries(session)

    if auth_required:
        if api_key:
            LOGGER.debug("Pyxis session using API key is created")
            session.headers.update({"X-API-KEY": api_key})
        elif cert and key:
            if os.path.exists(cert) and os.path.exists(key):
                LOGGER.debug("Pyxis session using cert + key is created")
                session.cert = (cert, key)
            else:
                raise ValueError(
                    "PYXIS_CERT_PATH or PYXIS_KEY_PATH does not point to a file that "
                    "exists."
                )
        else:
            # API key or cert + key need to be provided using env variable
            raise ValueError(
                "No auth details provided for Pyxis. "
                "Either define PYXIS_API_KEY or PYXIS_CERT_PATH + PYXIS_KEY_PATH"
            )
    else:
        LOGGER.debug("Pyxis session without authentication is created")

    if proxies:
        LOGGER.debug(
            "Pyxis session configured for Proxy (external preprod environment)"
        )
        session.proxies.update(proxies)

    return session


def post(url: str, body: Dict[str, Any]) -> Any:
    """
    POST pyxis API request to given URL with given payload

    Args:
        url (str): Pyxis API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Any: Pyxis response
    """
    session = _get_session(url)

    LOGGER.debug("POST Pyxis request: %s", url)
    resp = session.post(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "Pyxis POST query failed with %s - %s - %s",
            url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def put(url: str, body: Dict[str, Any]) -> Any:
    """
    PUT pyxis API request to given URL with given payload

    Args:
        url (str): Pyxis API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Any: Pyxis response
    """
    session = _get_session(url)

    LOGGER.debug("PATCH Pyxis request: %s", url)
    resp = session.put(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "Pyxis PUT query failed with %s - %s - %s",
            url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def patch(url: str, body: Dict[str, Any]) -> Any:
    """
    PATCH pyxis API request to given URL with given payload

    Args:
        url (str): Pyxis API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Any: Pyxis response
    """
    session = _get_session(url)

    LOGGER.debug("PATCH Pyxis request: %s", url)
    resp = session.patch(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "Pyxis PATCH query failed with %s - %s - %s",
            url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def get(
    url: str, params: Optional[Dict[str, Any]] = None, auth_required: bool = True
) -> Any:
    """
    Pyxis GET request

    Args:
        url (str): Pyxis URL
        params (dict): Additional query parameters
        auth_required (bool): Whether authentication should be required for the session

    Returns:
        Any: Pyxis GET request response
    """
    session = _get_session(url, auth_required=auth_required)
    LOGGER.debug("GET Pyxis request url: %s", url)
    LOGGER.debug("GET Pyxis request params: %s", params)
    resp = session.get(url, params=params)
    # Not raising exception for error statuses, because GET request can be used to check
    # if something exists. We don't want a 404 to cause failures.

    return resp


def get_project(base_url: str, project_id: str) -> Any:
    """
    Get project details for given project ID

    Args:
        base_url (str): Pyxis base URL
        project_id (str): certification project ID

    Returns:
       Any: Pyxis project response
    """
    session = _get_session(base_url)

    project_url = urljoin(base_url, f"v1/projects/certification/id/{project_id}")
    LOGGER.debug("Getting project details: %s", project_id)
    resp = session.get(project_url)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "Unable to get project details %s - %s - %s",
            project_url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def get_vendor_by_org_id(base_url: str, org_id: str) -> Any:
    """
    Get vendor using organization ID

    Args:
        base_url (str): Pyxis based API url
        org_id (str): Organization ID

    Returns:
        Any: Vendor Pyxis response
    """
    session = _get_session(base_url)

    project_url = urljoin(base_url, f"v1/vendors/org-id/{org_id}")
    LOGGER.debug("Getting project details by org_id: %s", org_id)
    resp = session.get(project_url)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "Unable to get vendor details %s - %s - %s",
            project_url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def get_repository_by_isv_pid(base_url: str, isv_pid: str) -> Any:
    """
    Get container repository using ISV pid

    Args:
        base_url (str): Pyxis based API url
        isv_pid (str): Project's isv_pid

    Returns:
        Any: Repository Pyxis response
    """
    session = _get_session(base_url)

    repo_url = urljoin(base_url, "v1/repositories")
    LOGGER.debug("Getting repository details by isv_pid: %s", isv_pid)
    query_filter = f"isv_pid=={isv_pid}"
    resp = session.get(repo_url, params={"filter": query_filter})

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "Unable to get repo details %s - %s - %s",
            repo_url,
            resp.status_code,
            resp.text,
        )
        raise
    json_resp = resp.json()
    return None if len(json_resp.get("data")) == 0 else json_resp["data"][0]


def post_image_request(
    base_url: str,
    project_id: str,
    image_id: str,
    operation: str,
) -> Any:
    """
    POST image request to Pyxis

    Args:
        base_url (str): base Pyxis URL,
        project_id (str): Certification project _id
        image_id (str): Container image _id
        operation (str): Operation type

    Returns:
        Any: Image request response
    """

    payload = {
        "operation": operation,
        "image_id": image_id,
    }

    image_request_url = urljoin(
        base_url, f"/v1/projects/certification/id/{project_id}/requests/images"
    )

    image_request = post(image_request_url, payload)

    return image_request


def now() -> datetime:
    """
    Return current time
    """
    return datetime.now()


def wait_for_image_request(
    base_url: str, image_request_id: str, timeout: float = 60 * 10, delay: float = 5
) -> Any:
    """
    Wait for image request to finish and transition to one of the final states.
    The request is tracked and status is printed every 5 seconds.

    Args:
        args (Any): CLI arguments
        image_request_id (str): Image request _id
        timeout (float): Timeout in seconds
        delay (float): Delay between status checks in seconds

    Returns:
        Any: Image request final response
    """
    image_request_url = urljoin(
        base_url, f"/v1/projects/certification/requests/images/id/{image_request_id}"
    )
    start_time = now()
    while True:
        resp = get(image_request_url)
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            LOGGER.exception(
                "Unable to get repo details %s - %s - %s",
                image_request_url,
                resp.status_code,
                resp.text,
            )
            raise
        image_request = resp.json()

        status = image_request["status"]
        LOGGER.info(
            "Image request %s status: %s",
            image_request_id,
            status,
        )
        if status in ("failed", "completed", "aborted"):
            LOGGER.info(
                "Image request %s finished with status %s - %s",
                image_request_id,
                status,
                image_request["status_message"],
            )
            return image_request
        if now() - start_time > timedelta(seconds=timeout):
            LOGGER.error(
                "Timeout: Waiting for image request failed: %s.", image_request_id
            )
            return image_request
        time.sleep(delay)


def wait_for_container_grades(
    base_url: str, image_identifier: str, timeout: float = 60 * 10, delay: float = 5
) -> Any:
    """
    Wait for container freshness grades to become available for
    the given image identifier.

    Args:
        base_url (str): Pyxis base URL
        image_identifier (str): Container image identifier
        timeout (float): Timeout in seconds
        delay (float): Delay between status checks in seconds
    """
    container_grades_url = urljoin(base_url, f"/v1/images/id/{image_identifier}")
    start_time = now()
    while True:
        resp = get(container_grades_url, params={"include": "freshness_grades,_id"})
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            LOGGER.exception(
                "Unable to get container image grades %s - %s - %s",
                container_grades_url,
                resp.status_code,
                resp.text,
            )
            raise
        container_image = resp.json()
        if container_image.get("freshness_grades"):
            LOGGER.info(
                "Container grades for %s are completed: %s",
                image_identifier,
                container_image["freshness_grades"],
            )
            return container_image
        LOGGER.info(
            "Waiting for container grades for %s: %s",
            image_identifier,
            container_image.get("freshness_grades"),
        )
        if now() - start_time > timedelta(seconds=timeout):
            LOGGER.error(
                "Timeout: Waiting for container grades failed: %s.", image_identifier
            )
            return container_image
        time.sleep(delay)
