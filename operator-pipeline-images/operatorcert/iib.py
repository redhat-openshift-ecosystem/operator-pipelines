"""II Builder API client"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from operatorcert.utils import add_session_retries
from requests_kerberos import HTTPKerberosAuth

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
    add_session_retries(
        session,
        # The IIB sometime returns 401/403 even with valid kerberos ticket
        status_forcelist=(401, 403, 408, 500, 502, 503, 504),
    )

    if kerberos_auth:
        session.auth = HTTPKerberosAuth()

    return session


def _get_request(get_url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """
    Get IIB response based on url and parameters

    Args:
        get_url (str): URL of IIB API
        params (Dict[str, Any]): get query parameters, defaults to None

    Returns:
        Any: IIB API response
    """
    session = get_session(False)

    resp = session.get(get_url, params=params)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "IIB GET query failed with %s and params %s - %s - %s",
            get_url,
            params,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def _post_request(post_url: str, body: Dict[str, Any]) -> Any:
    """
    Create IIB POST request

    Args:
        post_url (str): URL of IIB API
        body (Dict[str, Any]): Add build request payload

    Returns:
        Any: IIB api response
    """
    session = get_session()

    resp = session.post(post_url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "IIB POST query failed with %s - %s - %s",
            post_url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def add_builds(base_url: str, body: Dict[str, Any]) -> Any:
    """
    Add IIB build

    Args:
        base_url (str): Base URL of IIB API
        body (Dict[str, Any]): Add build request payload

    Returns:
        Any: IIB api response
    """
    add_build_url = urljoin(base_url, "api/v1/builds/add-rm-batch")

    return _post_request(add_build_url, body)


def add_fbc_build(base_url: str, body: Dict[str, Any]) -> Any:
    """
    Add IIB FBC fragment to index

    Args:
        base_url (str): Base URL of IIB API
        body (Dict[str, Any]): Add build request payload

    Returns:
        Any: IIB api response
    """
    add_build_url = urljoin(base_url, "api/v1/builds/fbc-operations")

    return _post_request(add_build_url, body)


def get_builds(base_url: str, batch_id: int) -> Any:
    """
    Get IIB build list based on batch id

    Args:
        base_url (str): Base URL of IIB API
        batch_id (int): Batch identifier

    Returns:
        Any: Build API response
    """

    get_builds_url = urljoin(base_url, "api/v1/builds")

    return _get_request(get_builds_url, params={"batch": batch_id})


def get_build(base_url: str, request_id: int) -> Any:
    """
    Get IIB build based on request id

    Args:
        base_url (str): Base URL of IIB API
        request_id (int): IIB identifier

    Returns:
        Any: Build API response
    """

    get_build_url = urljoin(base_url, f"api/v1/builds/{request_id}")

    return _get_request(get_build_url)


def wait_for_batch_results(
    iib_url: str, batch_id: int, timeout: float = 60 * 60, delay: float = 20
) -> Any:
    """
    Wait for IIB build till it finishes

    Args:
        iib_url (Any): CLI arguments
        batch_id (int): IIB batch identifier
        timeout ([type], optional): Maximum wait time. Defaults to 60*60 (3600 seconds/1 hour)
        delay (int, optional): Delay between build pollin. Defaults to 20.

    Returns:
        Any: Build response
    """
    start_time = datetime.now()
    loop = True

    while loop:
        response = get_builds(iib_url, batch_id)

        builds = response["items"]

        # all builds have completed
        if all(build.get("state") == "complete" for build in builds):
            LOGGER.info("IIB batch build completed successfully: %s", batch_id)
            return response
        # any have failed
        if any(build.get("state") == "failed" for build in builds):
            for build in builds:
                if build.get("state") == "failed":
                    LOGGER.error("IIB build failed: %s", build["id"])
                    reason = build.get("state_reason")
                    LOGGER.info("Reason: %s", reason)
            return response

        LOGGER.debug("Waiting for IIB batch build: %s", batch_id)
        LOGGER.debug("Current states [build id - state]:")
        for build in builds:
            LOGGER.debug("%s - %s", build["id"], build["state"])

        if datetime.now() - start_time > timedelta(seconds=timeout):
            LOGGER.error("Timeout: Waiting for IIB batch build failed: %s.", batch_id)
            break

        LOGGER.info("Waiting for IIB batch build to finish: %s", batch_id)
        time.sleep(delay)
    return None
