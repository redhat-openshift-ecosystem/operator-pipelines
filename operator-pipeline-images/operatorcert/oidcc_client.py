"""
Generic OIDC client.
"""

from dataclasses import dataclass
import logging
import os
from threading import Lock
import time
from typing import Any, Optional

import requests

from operatorcert.utils import add_session_retries

LOGGER = logging.getLogger("operator-cert")


class OIDCAuthenticationError(Exception):
    """
    Raised when token refresh fails
    """


@dataclass
class OIDCClientCredentials:
    """
    Container class for the authentication info necessary for the OIDC
    client credential flow

    Fields:
        token_url (str): The OAuth2/OIDC token endpoint. Can usually be obtained
            by fetching ${oidc_root}/.well-known/openid-configuration and extracting
            the token_endpoint field
        client_id (str): Client ID to be used to obtain a JWT token
        client_secret (str): Client secret to be used to obtain a JWT token
    """

    token_url: str
    client_id: str
    client_secret: str


class OIDCClientCredentialsClient:
    """
    Generic OIDC client credential client

    Transparently handles the OIDC client credential flow required for authentication,
    including automatic token renewal.
    """

    def __init__(
        self,
        auth: OIDCClientCredentials,
        proxy: Optional[str] = None,
    ):
        """
        Create a new client

        Args:
            auth (OIDCClientCredentials): Authentication info
            proxy (Optional[str]): Proxy to use to talk to the Hydra API.
                Defaults to None, which means no proxy.
        """
        self._auth = auth
        self._session = requests.Session()
        add_session_retries(self._session)
        if proxy:
            self._session.proxies["https"] = proxy
        self._token = ""
        self._token_expiration = 0
        self._token_mutex = Lock()

    def _token_expired(self) -> bool:
        """
        Check if the current token should be renewed

        Returns:
            bool: True if the current token needs to be renewed
        """
        # Avoid reusing a token which is too close to its expiration by considering it
        # expired if it has less than 15 seconds of validity left
        return time.time() > self._token_expiration - 15

    def _fetch_token(self) -> None:
        """
        Retrieve a new token using the OAuth2/OID client credential flow

        Raises:
            OIDCAuthenticationError: If the token renewal failed
        """
        # See https://www.oauth.com/oauth2-servers/access-tokens/client-credentials/
        # and https://www.ietf.org/rfc/rfc6749.txt section 4.4 and 2.3.1
        LOGGER.debug("Fetching new token from %s", self._auth.token_url)
        resp = requests.post(
            self._auth.token_url,
            {
                "grant_type": "client_credentials",
                "client_id": self._auth.client_id,
                "client_secret": self._auth.client_secret,
            },
        )
        if not resp.ok:
            LOGGER.error(
                "Unable to fetch auth token. [%s] %s", resp.status_code, resp.text
            )
            resp.raise_for_status()
        token = resp.json()
        if "access_token" not in token:
            if "error" in token:
                error_type = token["error"]
                error_description = token.get("error_description", "")
                error_msg = f"Authentication failed: {error_type} {error_description}"
            else:
                error_msg = "Authentication server did not provide a token"
            raise OIDCAuthenticationError(error_msg)
        self._token = token["access_token"]
        self._token_expiration = int(token.get("expires_in", 300) + time.time())
        self._session.headers["Authorization"] = "Bearer " + self._token
        LOGGER.debug("Token will expire in %s seconds", token.get("expires_in"))

    def _ensure_valid_token(self) -> None:
        """
        Check if we have a valid token and if not, renew it
        """
        with self._token_mutex:
            if self._token_expired():
                self._fetch_token()

    def _request(
        self,
        method: str,
        url: str,
        data: Any = None,
        params: Any = None,
    ) -> requests.Response:
        """
        Perform an HTTP request

        Args:
            method (str): HTTP method (GET, POST, ...)
            url (str): Relative URL of the endpoint. Will be combined with the base URL.
            data (Any, optional): Body of the request. Defaults to None.

        Returns:
            requests.Response: The response returned by the server
        """
        self._ensure_valid_token()
        LOGGER.debug("HTTP %s %s", method, url)
        return self._session.request(
            method,
            url,
            json=data,
            params=params,
        )

    def get(self, url: str, params: Any = None) -> Any:
        """
        Issue a JSON GET request

        Args:
            url (str): endpoint to call

        Returns:
            Any: JSON result
        """
        return self._request("get", url, params=params)
