"""
Github API client - should be replaced by github library
"""

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
            raise ValueError(
                "No auth details provided for Github. Define GITHUB_TOKEN."
            )

        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

    return session


def get(
    url: str, params: Optional[Dict[str, str]] = None, auth_required: bool = True
) -> Any:
    """
    Issue a GET request to the GitHub API

    Args:
        url (str): Github API URL
        params (dict): Additional query parameters
        auth_required (bool): Whether authentication should be required for the session

    Returns:
       Any: GitHub response
    """
    session = _get_session(auth_required=auth_required)
    LOGGER.debug("GET GitHub request url: %s", url)
    LOGGER.debug("GET GitHub request params: %s", params)
    resp = session.get(url, params=params)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "GitHub GET query failed with %s - %s - %s",
            url,
            resp.status_code,
            resp.text,
        )
        raise

    return resp.json()


def post(url: str, body: Dict[str, Any]) -> Any:
    """
    POST Github API request to given URL with given payload

    Args:
        url (str): Github API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Any: Github response
    """
    session = _get_session(auth_required=True)

    LOGGER.debug("POST Github request: %s", url)
    resp = session.post(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "GitHub POST query failed with %s - %s - %s",
            url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def patch(url: str, body: Dict[str, Any]) -> Any:
    """
    PATCH GitHub API request to given URL with given payload

    Args:
        url (str): Github API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Any: Github response
    """
    session = _get_session(auth_required=True)

    LOGGER.debug("PATCH Github request: %s", url)
    resp = session.patch(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "GitHub PATCH query failed with %s - %s - %s",
            url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()
