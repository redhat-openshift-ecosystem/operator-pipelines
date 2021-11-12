import logging
import os
from typing import Any, Dict

import requests

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
    token = os.environ.get("GITHUB_TOKEN")

    if auth_required and not token:
        raise Exception("No auth details provided for Github. Define GITHUB_TOKEN.")

    session = requests.Session()
    session.headers.update(
        {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    )
    return session


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
