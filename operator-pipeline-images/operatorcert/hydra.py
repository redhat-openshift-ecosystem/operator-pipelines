import logging
import os
import re
import sys
from typing import Any, Dict, Optional

import requests

from operatorcert.oidc_client import OIDCClientCredentials, OIDCClientCredentialsClient

LOGGER = logging.getLogger("operator-cert")


def get(url: str) -> Dict[str, Any]:
    """
    GET Hydra API request to given URL with given payload

    Args:
        url (str): Hydra API URL

    Returns:
        Dict[str, Any]: Hydra response
    """
    auth = OIDCClientCredentials(
        token_url=os.environ["HYDRA_SSO_TOKEN_URL"],
        client_id=os.environ["HYDRA_SSO_CLIENT_ID"],
        client_secret=os.environ["HYDRA_SSO_CLIENT_SECRET"],
    )

    # Set up proxy for preprod instances due to Akamai preprod lockdown
    regex = re.compile(r"^https:\/\/connect\.(dev|qa|stage)\.redhat\.com*")
    match = regex.match(url)
    proxy = None
    if match:
        proxy = "http://squid.corp.redhat.com:3128"

    client = OIDCClientCredentialsClient(auth, proxy)

    LOGGER.debug(f"GET Hydra API request: {url}")
    resp = client.get(url)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Hydra API GET query failed with {url} - {resp.status_code} - {resp.text}"
        )
        sys.exit(1)
    return resp.json()
