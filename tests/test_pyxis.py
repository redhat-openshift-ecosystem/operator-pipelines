from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from operatorcert import pyxis
from requests import HTTPError, Response


def test_is_internal(monkeypatch: Any) -> None:
    assert not pyxis.is_internal()

    monkeypatch.setenv("PYXIS_CERT_PATH", "/path/to/cert.pem")
    monkeypatch.setenv("PYXIS_KEY_PATH", "/path/to/key.key")

    assert pyxis.is_internal()


def test_get_session_api_key(monkeypatch: Any) -> None:
    monkeypatch.setenv("PYXIS_API_KEY", "123")
    session = pyxis._get_session()

    assert session.headers["X-API-KEY"] == "123"


def test_get_session_cert(monkeypatch: Any) -> None:
    monkeypatch.setenv("PYXIS_CERT_PATH", "/path/to/cert.pem")
    monkeypatch.setenv("PYXIS_KEY_PATH", "/path/to/key.key")
    session = pyxis._get_session()

    assert session.cert == ("/path/to/cert.pem", "/path/to/key.key")


def test_get_session_no_auth(monkeypatch: Any) -> None:
    with pytest.raises(Exception):
        pyxis._get_session()


@patch("operatorcert.pyxis._get_session")
def test_post(mock_session: MagicMock) -> None:
    mock_session.return_value.post.return_value.json.return_value = {"key": "val"}
    resp = pyxis.post("https://foo.com/v1/bar", {})

    assert resp == {"key": "val"}


@patch("operatorcert.pyxis._get_session")
def test_patch(mock_session: MagicMock) -> None:
    mock_session.return_value.patch.return_value.json.return_value = {"key": "val"}
    resp = pyxis.patch("https://foo.com/v1/bar", {})

    assert resp == {"key": "val"}


@patch("operatorcert.pyxis._get_session")
def test_patch_error(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.patch.return_value.raise_for_status.side_effect = (
        HTTPError(response=response)
    )
    with pytest.raises(HTTPError):
        pyxis.patch("https://foo.com/v1/bar", {})


@patch("operatorcert.pyxis._get_session")
def test_get(mock_session: MagicMock) -> None:
    mock_session.return_value.get.return_value = {"key": "val"}
    resp = pyxis.get("https://foo.com/v1/bar")

    assert resp == {"key": "val"}


@patch("operatorcert.pyxis._get_session")
def test_post_error(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.post.return_value.raise_for_status.side_effect = (
        HTTPError(response=response)
    )
    with pytest.raises(HTTPError):
        pyxis.post("https://foo.com/v1/bar", {})


@patch("operatorcert.pyxis._get_session")
def test_get_project(mock_session: MagicMock) -> None:
    mock_session.return_value.get.return_value.json.return_value = {"key": "val"}
    resp = pyxis.get_project("https://foo.com/v1", "123")

    assert resp == {"key": "val"}


@patch("operatorcert.pyxis._get_session")
def test_get_project_error(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.get.return_value.raise_for_status.side_effect = HTTPError(
        response=response
    )
    with pytest.raises(HTTPError):
        pyxis.get_project("https://foo.com/v1", "123")
