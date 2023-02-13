from typing import Any
from urllib.parse import parse_qsl, urlencode

import pytest
import requests

from operatorcert.oidc_client import (
    OIDCClientCredentials,
    OIDCClientCredentialsClient,
    OIDCAuthenticationError,
)


def test_client_credentials_flow_happy_path(requests_mock: Any) -> None:
    form_encoded_content_type = {"Content-Type": "application/x-www-form-urlencoded"}
    token_url = "https://auth.example.com/oidc/token"
    authorization_header = {"Authorization": "Bearer asdfghjkl"}
    token_response = {"access_token": "asdfghjkl", "expires_in": 600}
    api_response = {"foo": "bar"}
    proxy = "http://proxy.example.com:3128"

    requests_mock.post(
        token_url,
        request_headers=form_encoded_content_type,
        json=token_response,
    )
    requests_mock.get(
        "https://api.example.com/v1/hello",
        request_headers=authorization_header,
        json=api_response,
    )

    auth = OIDCClientCredentials(
        token_url=token_url, client_id="abc", client_secret="xyz"
    )
    oidc = OIDCClientCredentialsClient(auth, proxy=proxy)
    assert oidc.get("https://api.example.com/v1/hello").json() == api_response
    assert requests_mock.call_count == 2  # 1 token post + 1 api get
    history = {x.hostname: x for x in requests_mock.request_history}
    assert "auth.example.com" in history
    assert "api.example.com" in history
    assert history["api.example.com"].proxies.get("https") == proxy
    assert history["auth.example.com"].proxies.get("https") is None
    auth_body = parse_qsl(history["auth.example.com"].text)
    assert ("grant_type", "client_credentials") in auth_body
    assert ("client_id", auth.client_id) in auth_body
    assert ("client_secret", auth.client_secret) in auth_body
    requests_mock.reset_mock()
    assert oidc.get("https://api.example.com/v1/hello").json() == api_response
    assert requests_mock.call_count == 1  # 1 api get, no token requests
    assert requests_mock.request_history[0].hostname == "api.example.com"
    assert requests_mock.request_history[0].method == "GET"


def test_client_credentials_flow_unhappy_path(requests_mock: Any) -> None:
    form_encoded_content_type = {"Content-Type": "application/x-www-form-urlencoded"}
    token_error_url = "https://auth.example.com/oidc/fail/token"
    token_error_response = {
        "error": "unauthorized_client",
        "error_description": "Invalid client secret",
    }
    token_invalid_url = "https://auth.example.com/oidc/invalid/token"
    token_invalid_response = {"something": "else"}
    api_response = {"foo": "bar"}

    requests_mock.post(
        token_error_url,
        request_headers=form_encoded_content_type,
        json=token_error_response,
    )
    requests_mock.post(
        token_invalid_url,
        request_headers=form_encoded_content_type,
        json=token_invalid_response,
    )
    requests_mock.get(
        "https://api.example.com/v1/hello",
        request_headers={"Authorization": "Bearer asdfghjkl"},
        json=api_response,
    )

    auth = OIDCClientCredentials(
        token_url=token_error_url, client_id="abc", client_secret="xyz"
    )
    oidc = OIDCClientCredentialsClient(auth)
    with pytest.raises(OIDCAuthenticationError) as error:
        oidc.get("https://api.example.com/v1/hello")
    assert "unauthorized_client" in str(error.value)
    assert requests_mock.call_count == 1  # 1 failed token request, no api calls
    assert requests_mock.request_history[0].hostname == "auth.example.com"
    requests_mock.reset_mock()

    auth = OIDCClientCredentials(
        token_url=token_invalid_url, client_id="abc", client_secret="xyz"
    )
    oidc = OIDCClientCredentialsClient(auth)
    with pytest.raises(OIDCAuthenticationError):
        oidc.get("https://api.example.com/v1/hello")
    assert requests_mock.call_count == 1  # 1 failed token request, no api calls
    assert requests_mock.request_history[0].hostname == "auth.example.com"


def test_client_credentials_flow_http_error(requests_mock: Any) -> None:
    form_encoded_content_type = {"Content-Type": "application/x-www-form-urlencoded"}
    token_error_url = "https://auth.example.com/oidc/fail/token"

    requests_mock.post(
        token_error_url,
        request_headers=form_encoded_content_type,
        status_code=500,
    )

    auth = OIDCClientCredentials(
        token_url=token_error_url, client_id="abc", client_secret="xyz"
    )
    oidc = OIDCClientCredentialsClient(auth)
    with pytest.raises(requests.exceptions.HTTPError):
        oidc.get("https://api.example.com/v1/hello")
