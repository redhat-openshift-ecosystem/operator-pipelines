from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from operatorcert import github
from requests import HTTPError, Response


def test_get_session_github_token(monkeypatch: Any) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "123")
    session = github._get_session(auth_required=True)

    assert session.headers["Authorization"] == "Bearer 123"


def test_get_session_no_auth() -> None:
    session = github._get_session(auth_required=False)
    assert "Authorization" not in session.headers


def test_get_session_missing_token() -> None:
    with pytest.raises(Exception):
        github._get_session(auth_required=True)


@patch("operatorcert.github._get_session")
def test_get(mock_session: MagicMock) -> None:
    mock_session.return_value.get.return_value.json.return_value = {"key": "val"}
    resp = github.get("https://foo.com/v1/bar", {})
    assert resp == {"key": "val"}


@patch("operatorcert.github._get_session")
def test_get_with_error(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 500
    mock_session.return_value.get.return_value.raise_for_status.side_effect = HTTPError(
        response=response
    )
    with pytest.raises(HTTPError):
        github.get("https://foo.com/v1/bar", {})


@patch("operatorcert.github._get_session")
def test_post(mock_session: MagicMock) -> None:
    mock_session.return_value.post.return_value.json.return_value = {"key": "val"}
    resp = github.post("https://foo.com/v1/bar", {})

    assert resp == {"key": "val"}


@patch("operatorcert.github._get_session")
def test_post_with_error(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.post.return_value.raise_for_status.side_effect = (
        HTTPError(response=response)
    )
    with pytest.raises(HTTPError):
        github.post("https://foo.com/v1/bar", {})


@patch("operatorcert.github._get_session")
def test_patch(mock_session: MagicMock) -> None:
    mock_session.return_value.patch.return_value.json.return_value = {"key": "val"}
    resp = github.patch("https://foo.com/v1/bar", {})

    assert resp == {"key": "val"}


@patch("operatorcert.github._get_session")
def test_patch_with_error(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.patch.return_value.raise_for_status.side_effect = (
        HTTPError(response=response)
    )
    with pytest.raises(HTTPError):
        github.patch("https://foo.com/v1/bar", {})
