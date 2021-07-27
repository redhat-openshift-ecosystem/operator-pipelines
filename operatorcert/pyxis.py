import logging
import os
from typing import Any, Dict

import requests

LOGGER = logging.getLogger("operator-cert")


def post_with_api_key(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.environ.get("PYXIS_API_KEY")
    if not api_key:
        raise Exception("Pyxis API key is missing. Define PYXIS_API_KEY env variable")

    LOGGER.debug(f"POST Pyxis request: {url}")
    resp = requests.post(url, json=body, headers={"X-API-KEY": api_key})

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Pyxis POST query failed with {url} - {resp.status_code} - {resp.text}"
        )
        raise
    return resp.json()
