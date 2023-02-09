from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from requests import HTTPError, Response

from operatorcert import hydra


def test_get(requests_mock: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("HYDRA_SSO_TOKEN_URL", "https://auth.example.com/oidc/token")
    monkeypatch.setenv("HYDRA_SSO_CLIENT_ID", "abc")
    monkeypatch.setenv("HYDRA_SSO_CLIENT_SECRET", "xyz")

    requests_mock.post(
        "https://auth.example.com/oidc/token",
        request_headers={"Content-Type": "application/x-www-form-urlencoded"},
        json={"access_token": "asdfghjkl", "expires_in": 600},
    )
    requests_mock.get(
        "https://connect.redhat.com/foo/bar",
        request_headers={"Authorization": "Bearer asdfghjkl"},
        json={"key": "val"},
    )

    resp = hydra.get("https://connect.redhat.com/foo/bar")

    assert resp == {"key": "val"}


def test_get_preprod_proxy(requests_mock: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("HYDRA_SSO_TOKEN_URL", "https://auth.example.com/oidc/token")
    monkeypatch.setenv("HYDRA_SSO_CLIENT_ID", "abc")
    monkeypatch.setenv("HYDRA_SSO_CLIENT_SECRET", "xyz")

    requests_mock.post(
        "https://auth.example.com/oidc/token",
        request_headers={"Content-Type": "application/x-www-form-urlencoded"},
        json={"access_token": "asdfghjkl", "expires_in": 600},
    )
    requests_mock.get(
        "https://connect.dev.redhat.com/foo/bar",
        request_headers={"Authorization": "Bearer asdfghjkl"},
        json={"key": "val"},
    )

    resp = hydra.get("https://connect.dev.redhat.com/foo/bar")
    assert resp == {"key": "val"}
    history = {x.hostname: x for x in requests_mock.request_history}
    assert (
        history["connect.dev.redhat.com"].proxies.get("https")
        == "http://squid.corp.redhat.com:3128"
    )


def test_get_with_error(requests_mock: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("HYDRA_SSO_TOKEN_URL", "https://auth.example.com/oidc/token")
    monkeypatch.setenv("HYDRA_SSO_CLIENT_ID", "abc")
    monkeypatch.setenv("HYDRA_SSO_CLIENT_SECRET", "xyz")

    requests_mock.post(
        "https://auth.example.com/oidc/token",
        request_headers={"Content-Type": "application/x-www-form-urlencoded"},
        json={"access_token": "asdfghjkl", "expires_in": 600},
    )
    requests_mock.get(
        "https://connect.dev.redhat.com/foo/bar",
        request_headers={"Authorization": "Bearer asdfghjkl"},
        status_code=404,
    )

    with pytest.raises(SystemExit):
        hydra.get("https://connect.dev.redhat.com/foo/bar")
