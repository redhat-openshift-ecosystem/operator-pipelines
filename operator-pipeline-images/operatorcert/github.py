import logging
import os
from typing import Any, Dict, Optional

import requests

from operatorcert.utils import add_session_retries

LOGGER = logging.getLogger("operator-cert")


def _get_session(auth_required: bool = False) -> requests.Session:
    """
    Create a Github http session with auth based on env variables.

    Auth is set to use OAuth token if auth is required.

    Args:
        auth_required (bool): Whether authentication should be required for the session

    Raises:
        Exception: Exception is raised when auth ENV variables are missing.

    Returns:
        requests.Session: Github session
    """
    session = requests.Session()
    add_session_retries(session)

    if auth_required:
        token = os.environ.get("GITHUB_TOKEN")

        if not token:
            raise Exception("No auth details provided for Github. Define GITHUB_TOKEN.")

        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

    return session


def get(
    url: str, params: Optional[Dict[str, str]] = None, auth_required: bool = True
) -> Dict[str, Any]:
    """
    Issue a GET request to the GitHub API

    Args:
        url (str): Github API URL
        params (dict): Additional query parameters
        auth_required (bool): Whether authentication should be required for the session

    Returns:
        Dict[str, Any]: GitHub response
    """
    session = _get_session(auth_required=auth_required)
    LOGGER.debug(f"GET GitHub request url: {url}")
    LOGGER.debug(f"GET GitHub request params: {params}")
    resp = session.get(url, params=params)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"GitHub GET query failed with {url} - {resp.status_code} - {resp.text}"
        )
        raise

    return resp.json()


def post(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST Github API request to given URL with given payload

    Args:
        url (str): Github API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Dict[str, Any]: Github response
    """
    session = _get_session(auth_required=True)

    LOGGER.debug(f"POST Github request: {url}")
    resp = session.post(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Github POST query failed with {url} - {resp.status_code} - {resp.text}"
        )
        raise
    return resp.json()


def patch(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    PATCH GitHub API request to given URL with given payload

    Args:
        url (str): Github API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Dict[str, Any]: Github response
    """
    session = _get_session(auth_required=True)

    LOGGER.debug(f"PATCH Github request: {url}")
    resp = session.patch(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Github PATCH query failed with {url} - {resp.status_code} - {resp.text}"
        )
        raise
    return resp.json()
