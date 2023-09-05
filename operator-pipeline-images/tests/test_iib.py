from unittest.mock import patch, MagicMock

import pytest
from requests import HTTPError, Response
from requests_kerberos import HTTPKerberosAuth

from operatorcert import iib


def test_get_session() -> None:
    session = iib.get_session()
    assert isinstance(session.auth, HTTPKerberosAuth)


@patch("operatorcert.iib.get_session")
def test_add_builds(mock_session: MagicMock) -> None:
    mock_session.return_value.post.return_value.json.return_value = {"key": "val"}
    resp = iib.add_builds("https://foo.com/v1/", {})

    assert resp == {"key": "val"}


@patch("operatorcert.iib.get_session")
def test_add_builds_400(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.post.return_value.raise_for_status.side_effect = (
        HTTPError(response=response)
    )

    with pytest.raises(HTTPError):
        iib.add_builds("https://foo.com/v1/bar", {})


@patch("operatorcert.iib.get_session")
def test_get_builds(mock_session: MagicMock) -> None:
    mock_session.return_value.get.return_value.json.return_value = {"key": "val"}
    resp = iib.get_builds("https://foo.com/v1/", 1)

    assert resp == {"key": "val"}


@patch("operatorcert.iib.get_session")
def test_get_builds_404(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 404
    mock_session.return_value.get.return_value.raise_for_status.side_effect = HTTPError(
        response=response
    )

    with pytest.raises(HTTPError):
        iib.get_builds("https://foo.com/v1/bar", 1)
