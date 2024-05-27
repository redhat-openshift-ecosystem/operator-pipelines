from unittest.mock import patch, MagicMock

import pytest
from requests import HTTPError, Response
from requests_kerberos import HTTPKerberosAuth

from operatorcert import iib


def test_get_session() -> None:
    session = iib.get_session()
    assert isinstance(session.auth, HTTPKerberosAuth)


@patch("operatorcert.iib.get_session")
def test__post_request(mock_session: MagicMock) -> None:
    mock_session.return_value.post.return_value.json.return_value = {"key": "val"}
    resp = iib._post_request("https://foo.com/v1/", {})

    assert resp == {"key": "val"}


@patch("operatorcert.iib.get_session")
def test__post_request_400(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 400
    mock_session.return_value.post.return_value.raise_for_status.side_effect = (
        HTTPError(response=response)
    )

    with pytest.raises(HTTPError):
        iib._post_request("https://foo.com/v1/bar", {})


@patch("operatorcert.iib._post_request")
def test_add_builds(mock_request: MagicMock) -> None:
    iib.add_builds("https://foo.com/v1/", {})

    mock_request.assert_called_once_with(
        "https://foo.com/v1/api/v1/builds/add-rm-batch", {}
    )


@patch("operatorcert.iib._post_request")
def test_add_fbc_fragment_builds(mock_request: MagicMock) -> None:
    iib.add_fbc_build("https://foo.com/v1/", {})

    mock_request.assert_called_once_with(
        "https://foo.com/v1/api/v1/builds/fbc-operations", {}
    )


@patch("operatorcert.iib.get_session")
def test__get_request(mock_session: MagicMock) -> None:
    mock_session.return_value.get.return_value.json.return_value = {"key": "val"}
    resp = iib._get_request("https://foo.com/v1/", {})

    assert resp == {"key": "val"}


@patch("operatorcert.iib.get_session")
def test__get_request_404(mock_session: MagicMock) -> None:
    response = Response()
    response.status_code = 404
    mock_session.return_value.get.return_value.raise_for_status.side_effect = HTTPError(
        response=response
    )

    with pytest.raises(HTTPError):
        iib._get_request("https://foo.com/v1/bar", {})


@patch("operatorcert.iib._get_request")
def test_get_builds(mock_request: MagicMock) -> None:
    iib.get_builds("https://foo.com/v1/", 1)

    mock_request.assert_called_once_with(
        "https://foo.com/v1/api/v1/builds", params={"batch": 1}
    )


@patch("operatorcert.iib._get_request")
def test_get_build(mock_request: MagicMock) -> None:
    iib.get_build("https://foo.com/v1/", 1)

    mock_request.assert_called_once_with("https://foo.com/v1/api/v1/builds/1")
