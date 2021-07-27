from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from operatorcert.pyxis import post_with_api_key
from requests import HTTPError, Response


@patch("requests.post")
def test_post_with_api_key(mock_post: MagicMock, monkeypatch: Any) -> None:
    mock_post.return_value.json.return_value = {"key": "val"}
    monkeypatch.setenv("PYXIS_API_KEY", "123")
    resp = post_with_api_key("https://foo.com/v1/bar", {})

    assert resp == {"key": "val"}


@patch("requests.post")
def test_post_with_api_key_missing_key(mock_post: MagicMock, monkeypatch: Any) -> None:
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
