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
    session = pyxis._get_session("test")

    assert session.headers["X-API-KEY"] == "123"


def test_get_session_proxy(monkeypatch: Any) -> None:
    monkeypatch.setenv("PYXIS_API_KEY", "123")
    session = pyxis._get_session("test-qa")

    assert session.proxies == {
        "http": "http://squid.corp.redhat.com:3128",
        "https": "http://squid.corp.redhat.com:3128",
    }


@patch("os.path.exists")
def test_get_session_cert(mock_path_exists: MagicMock, monkeypatch: Any) -> None:
    mock_path_exists.return_value = True
    monkeypatch.setenv("PYXIS_CERT_PATH", "/path/to/cert.pem")
    monkeypatch.setenv("PYXIS_KEY_PATH", "/path/to/key.key")
    session = pyxis._get_session("test")

    assert session.cert == ("/path/to/cert.pem", "/path/to/key.key")


@patch("os.path.exists")
def test_get_session_cert_not_exist(
    mock_path_exists: MagicMock, monkeypatch: Any
) -> None:
    mock_path_exists.return_value = False
    monkeypatch.setenv("PYXIS_CERT_PATH", "/path/to/cert.pem")
    monkeypatch.setenv("PYXIS_KEY_PATH", "/path/to/key.key")

    with pytest.raises(Exception):
        pyxis._get_session("test")


def test_get_session_no_auth() -> None:
    session = pyxis._get_session("test", auth_required=False)
    assert session.cert is None
    assert session.headers.get("X-API-KEY") is None


def test_get_session_no_credentials(monkeypatch: Any) -> None:
    with pytest.raises(Exception):
        pyxis._get_session("test")


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
def test_put(mock_session: MagicMock) -> None:
    mock_session.return_value.put.return_value.json.return_value = {"key": "val"}
    resp = pyxis.put("https://foo.com/v1/bar", {})

    assert resp == {"key": "val"}


@patch("operatorcert.pyxis._get_session")
def test_put_error(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.put.return_value.raise_for_status.side_effect = HTTPError(
        response=response
    )
    with pytest.raises(HTTPError):
        pyxis.put("https://foo.com/v1/bar", {})


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


@patch("operatorcert.pyxis._get_session")
def test_get_vendor_by_org_id(mock_session: MagicMock) -> None:
    mock_session.return_value.get.return_value.json.return_value = {"key": "val"}
    resp = pyxis.get_vendor_by_org_id("https://foo.com/v1", "123")

    assert resp == {"key": "val"}


@patch("operatorcert.pyxis._get_session")
def test_get_vendor_by_org_id_error(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.get.return_value.raise_for_status.side_effect = HTTPError(
        response=response
    )
    with pytest.raises(HTTPError):
        pyxis.get_vendor_by_org_id("https://foo.com/v1", "123")


@patch("operatorcert.pyxis._get_session")
def test_get_repository_by_isv_pid(mock_session: MagicMock) -> None:
    mock_session.return_value.get.return_value.json.return_value = {
        "data": [{"key": "val"}]
    }
    resp = pyxis.get_repository_by_isv_pid("https://foo.com/v1", "123")

    assert resp == {"key": "val"}


@patch("operatorcert.pyxis._get_session")
def test_get_repository_by_isv_pid_error(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.get.return_value.raise_for_status.side_effect = HTTPError(
        response=response
    )
    with pytest.raises(HTTPError):
        pyxis.get_repository_by_isv_pid("https://foo.com/v1", "123")
