import logging
import os
from typing import Any, Dict
from urllib.parse import urljoin

import requests
from requests.sessions import session

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


def _get_session() -> requests.Session:
    """
    Create a Pyxis http session with auth based on env variables.

    Auth is set to use either API key or certificate + key.

    Raises:
        Exception: Exception is raised when auth ENV variables are missing.

    Returns:
        requests.Session: Pyxis session
    """
    api_key = os.environ.get("PYXIS_API_KEY")
    cert = os.environ.get("PYXIS_CERT_PATH")
    key = os.environ.get("PYXIS_KEY_PATH")

    # API key or cert + key need to be provided using env variable
    if not api_key and (not cert or not key):
        raise Exception(
            "No auth details provided for Pyxis. "
            "Either define PYXIS_API_KEY or PYXIS_CERT_PATH + PYXIS_KEY_PATH"
        )

    session = requests.Session()
    if api_key:
        LOGGER.debug("Pyxis session using API key is created")
        session.headers.update({"X-API-KEY": api_key})
    else:
        LOGGER.debug("Pyxis session using cert + key is created")
        session.cert = (cert, key)
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
    session = _get_session()

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


def patch(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    PATCH pyxis API request to given URL with given payload

    Args:
        url (str): Pyxis API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Dict[str, Any]: Pyxis response
    """
    session = _get_session()

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
    session = _get_session()
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
    session = _get_session()

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
