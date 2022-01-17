import logging
import os
import re
import sys
from typing import Any, Dict

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


LOGGER = logging.getLogger("operator-cert")


def _get_session() -> requests.Session:
    """
    Create a Hydra http session with auth based on env variables.

    Auth is set to use Basic Auth.

    Returns:
        requests.Session: Hydra session
    """
    username = os.environ.get("HYDRA_USERNAME")
    password = os.environ.get("HYDRA_PASSWORD")
    if not username or not password:
        LOGGER.error(
            "Missing auth details for Hydra. Define both HYDRA_USERNAME and HYDRA_PASSWORD."
        )
        sys.exit(1)

    session = requests.Session()
    session.auth = (username, password)

    # Exponential retry backoff for a max wait of ~8.5 mins
    retries = Retry(
        total=10, backoff_factor=1, status_forcelist=(408, 500, 502, 503, 504)
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def get(url: str) -> Dict[str, Any]:
    """
    GET Hydra API request to given URL with given payload

    Args:
        url (str): Hydra API URL

    Returns:
        Dict[str, Any]: Hydra response
    """
    session = _get_session()

    # Set up proxy for preprod instances due to Akamai preprod lockdown
    regex = re.compile(r"^https:\/\/connect\.(dev|qa|stage)\.redhat\.com*")
    match = regex.match(url)
    if match:
        session.proxies["https"] = "http://squid.corp.redhat.com:3128"

    LOGGER.debug(f"GET Hydra API request: {url}")
    resp = session.get(url)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Hydra API GET query failed with {url} - {resp.status_code} - {resp.text}"
        )
        sys.exit(1)
    return resp.json()
