from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from operatorcert.pyxis import post_with_api_key, post_with_cert, get_with_cert
from requests import HTTPError, Response


@patch("requests.post")
def test_post_with_api_key(mock_post: MagicMock, monkeypatch: Any) -> None:
    mock_post.return_value.json.return_value = {"key": "val"}
    monkeypatch.setenv("PYXIS_API_KEY", "123")
    resp = post_with_api_key("https://foo.com/v1/bar", {})

    assert resp == {"key": "val"}


@patch("requests.post")
def test_post_with_api_key_missing_key(mock_post: MagicMock) -> None:
    mock_post.return_value.json.return_value = {"key": "val"}
    with pytest.raises(Exception):
        post_with_api_key("https://foo.com/v1/bar", {})


@patch("requests.post")
def test_post_with_api_key_error(mock_post: MagicMock, monkeypatch: Any) -> None:
    monkeypatch.setenv("PYXIS_API_KEY", "123")
    response = Response()
    response.status_code = 400
    mock_post.return_value.raise_for_status.side_effect = HTTPError(response=response)
    with pytest.raises(HTTPError):
        post_with_api_key("https://foo.com/v1/bar", {})


@patch("os.path.exists")
@patch("requests.post")
def test_post_with_cert(mock_post: MagicMock, mock_exists: MagicMock) -> None:
    mock_post.return_value.json.return_value = {"key": "val"}
    mock_exists.return_value = True
    resp = post_with_cert("https://foo.com/v1/bar", {}, "cert.path", "key.path")

    assert resp == {"key": "val"}


@patch("os.path.exists")
def test_post_with_cert_missing_cert(mock_exists: MagicMock) -> None:
    mock_exists.return_value = False
    with pytest.raises(Exception):
        post_with_cert("https://foo.com/v1/bar", {}, "cert.path", "key.path")


@patch("os.path.exists")
def test_post_with_cert_missing_key(mock_exists: MagicMock) -> None:
    mock_exists.side_effect = [True, False]
    with pytest.raises(Exception):
        post_with_cert("https://foo.com/v1/bar", {}, "cert.path", "key.path")


@patch("os.path.exists")
@patch("requests.post")
def test_post_with_cert_error(mock_post: MagicMock, mock_exists: MagicMock) -> None:
    mock_exists.return_value = True
    response = Response()
    response.status_code = 400
    mock_post.return_value.raise_for_status.side_effect = HTTPError(response=response)
    with pytest.raises(HTTPError):
        post_with_cert("https://foo.com/v1/bar", {}, "cert.path", "key.path")


@patch("os.path.exists")
@patch("requests.get")
def test_get_with_cert(mock_get: MagicMock, mock_exists: MagicMock) -> None:
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"key": "val"}
    mock_exists.return_value = True
    resp = get_with_cert("https://foo.com/v1/bar", "cert.path", "key.path")

    assert resp.status_code == 200
    assert resp.json() == {"key": "val"}


@patch("os.path.exists")
def test_get_with_cert_missing_cert(mock_exists: MagicMock) -> None:
    mock_exists.return_value = False
    with pytest.raises(Exception):
        get_with_cert("https://foo.com/v1/bar", "cert.path", "key.path")


@patch("os.path.exists")
def test_get_with_cert_missing_key(mock_exists: MagicMock) -> None:
    mock_exists.side_effect = [True, False]
    with pytest.raises(Exception):
        get_with_cert("https://foo.com/v1/bar", "cert.path", "key.path")


@patch("os.path.exists")
@patch("requests.get")
def test_get_with_cert_no_error(mock_get: MagicMock, mock_exists: MagicMock) -> None:
    mock_exists.return_value = True
    response = Response()
    response.status_code = 400
    mock_get.return_value.raise_for_status.side_effect = HTTPError(response=response)
    get_with_cert("https://foo.com/v1/bar", "cert.path", "key.path")
