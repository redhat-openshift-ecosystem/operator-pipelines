"""II Builder API client"""
import logging
from typing import Any, Dict
from urllib.parse import urljoin

import requests
from requests_kerberos import HTTPKerberosAuth

from operatorcert.utils import add_session_retries

LOGGER = logging.getLogger("operator-cert")


def get_session(kerberos_auth: bool = True) -> Any:
    """
    Get IIB requests session

    Args:
        kerberos_auth (bool, optional): Session uses kerberos auth. Defaults to True.

    Returns:
        Any: IIB session
    """
    session = requests.Session()
    add_session_retries(session)

    if kerberos_auth:
        session.auth = HTTPKerberosAuth()

    return session


def add_builds(base_url: str, body: Dict[str, Any]) -> Any:
    """
    Add IIB build

    Args:
        base_url (str): Base URL of IIB API
        body (Dict[str, Any]): Add build request payload

    Returns:
        Any: IIB api response
    """
    session = get_session()

    add_build_url = urljoin(base_url, "api/v1/builds/add-rm-batch")

    resp = session.post(add_build_url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "IIB POST query failed with %s - %s - %s",
            add_build_url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def get_builds(base_url: str, batch_id: int) -> Any:
    """
    Get IIB build list based on batch id

    Args:
        base_url (str): Base URL of IIB API
        batch_id (int): Batch identifier

    Returns:
        Any: Build API response
    """

    session = get_session(False)

    add_build_url = urljoin(base_url, "api/v1/builds")

    resp = session.get(add_build_url, params={"batch": batch_id})

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "IIB GET query failed with %s and batch %s - %s - %s",
            add_build_url,
            batch_id,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()
