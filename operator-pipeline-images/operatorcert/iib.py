import logging
from typing import Any, Dict
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests_kerberos import HTTPKerberosAuth

LOGGER = logging.getLogger("operator-cert")


def get_session(kerberos_auth=True) -> Any:
    """
    Get IIB requests session

    Args:
        kerberos_auth (bool, optional): Session uses kerberos auth. Defaults to True.

    Returns:
        Any: IIB session
    """
    session = requests.Session()

    if kerberos_auth:
        session.auth = HTTPKerberosAuth()

    # Exponential retry backoff for a max wait of ~8.5 mins
    retries = Retry(
        total=10, backoff_factor=1, status_forcelist=(408, 500, 502, 503, 504)
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

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

    add_build_url = urljoin(base_url, f"api/v1/builds/add-rm-batch")

    resp = session.post(add_build_url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"IIB POST query failed with {add_build_url} - {resp.status_code} - {resp.text}"
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

    add_build_url = urljoin(base_url, f"api/v1/builds")

    resp = session.get(add_build_url, params={"batch": batch_id})

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"IIB GET query failed with {add_build_url} and batch {batch_id} - "
            f"{resp.status_code} - {resp.text}"
        )
        raise
    return resp.json()
