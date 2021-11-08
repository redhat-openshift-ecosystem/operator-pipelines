from typing import Any
from unittest.mock import MagicMock, patch

from operatorcert import hydra
from requests import HTTPError, Response


def test_get_session_basic_auth(monkeypatch: Any) -> None:
    monkeypatch.setenv("HYDRA_USERNAME", "user")
    monkeypatch.setenv("HYDRA_PASSWORD", "password")

    session = hydra._get_session()
    assert session.auth == ("user", "password")


@patch("sys.exit")
def test_get_session_no_auth(mock_exit: MagicMock) -> None:
    hydra._get_session()
    mock_exit.assert_called_once_with(1)


@patch("operatorcert.hydra._get_session")
def test_get(mock_session: MagicMock) -> None:
    mock_session.return_value.get.return_value.json.return_value = {"key": "val"}
    resp = hydra.get("https://foo.com/v1/bar")

    assert resp == {"key": "val"}


@patch("operatorcert.hydra._get_session")
def test_get_preprod_proxy(mock_session: MagicMock) -> None:
    mock_session.return_value.get.return_value.json.return_value = {"key": "val"}

    resp = hydra.get("https://connect.dev.redhat.com/foo/bar")
    assert resp == {"key": "val"}


@patch("sys.exit")
@patch("operatorcert.hydra._get_session")
def test_get_with_error(mock_session: MagicMock, mock_exit: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.get.return_value.raise_for_status.side_effect = HTTPError(
        response=response
    )
    hydra.get("https://foo.com/v1/bar")
    mock_exit.assert_called_once_with(1)
