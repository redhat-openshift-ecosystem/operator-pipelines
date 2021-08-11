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


def post_with_cert(
    url: str, body: Dict[str, Any], cert_path: str, key_path: str
) -> Dict[str, Any]:
    if not os.path.exists(cert_path):
        raise Exception(f"Pyxis cert at path {cert_path} is missing.")
    if not os.path.exists(key_path):
        raise Exception(f"Pyxis key at path {key_path} is missing.")

    LOGGER.debug(f"POST Pyxis request: {url}")
    resp = requests.post(url, json=body, cert=(cert_path, key_path))

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            f"Pyxis POST query failed with {url} - {resp.status_code} - {resp.text}"
        )
        raise
    return resp.json()


def get_with_cert(url: str, cert_path: str, key_path: str) -> Dict[str, Any]:
    if not os.path.exists(cert_path):
        raise Exception(f"Pyxis cert at path {cert_path} is missing.")
    if not os.path.exists(key_path):
        raise Exception(f"Pyxis key at path {key_path} is missing.")

    LOGGER.debug(f"GET Pyxis request: {url}")
    resp = requests.get(url, cert=(cert_path, key_path))
    # Not raising exception for error statuses, because GET request can be used to check
    # if something exists. We don't want a 404 to cause failures.

    return resp
