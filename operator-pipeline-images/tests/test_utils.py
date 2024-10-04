import os
import subprocess
from pathlib import Path
from typing import Dict, List
from unittest import mock
from unittest.mock import MagicMock, call, patch

import pytest
from operatorcert import utils
from operatorcert.utils import store_results
from requests import HTTPError, Session
from requests.adapters import HTTPAdapter


def test_find_file(tmp_path: Path) -> None:
    tmp_path.joinpath("foo", "bar").mkdir(parents=True)
    tmp_path.joinpath("foo", "baz.txt").touch()
    tmp_path.joinpath("foo", "bar", "baz.txt").touch()
    result = utils.find_file(
        tmp_path,
        [
            ("foo", "not-found.txt"),
            ("foo", "bar", "baz.txt"),
            ("foo", "baz.txt"),
        ],
    )
    assert result is not None
    assert str(result.relative_to(tmp_path)) == "foo/bar/baz.txt"

    result = utils.find_file(
        tmp_path,
        [
            ("foo", "not-found.txt"),
        ],
    )
    assert result is None


def test_store_results() -> None:
    results = {
        "example_name": "example_value",
        "other_name": "other_value",
        "third_name": {"some": "dict"},
        "none": None,
    }
    mock_open = mock.mock_open()
    with mock.patch("builtins.open", mock_open):
        store_results(results)

    assert mock_open.call_count == 4
    assert mock_open.call_args_list == [
        call("example_name", "w", encoding="utf-8"),
        call("other_name", "w", encoding="utf-8"),
        call("third_name", "w", encoding="utf-8"),
        call("none", "w", encoding="utf-8"),
    ]


def test_set_client_keytab() -> None:
    utils.set_client_keytab("")

    with pytest.raises(IOError):
        utils.set_client_keytab("non-existent")

    with mock.patch("os.path.isfile") as mock_isfile:
        mock_isfile.return_value = True
        utils.set_client_keytab("test")
        assert os.environ["KRB5_CLIENT_KTNAME"] == "FILE:test"


def test_add_session_retries() -> None:
    status_forcelist = (404, 503)
    total = 3
    backoff_factor = 0.5
    session = Session()
    utils.add_session_retries(
        session,
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    # Check adapter types for HTTPAdapter to pass mypy
    assert isinstance(session.adapters["http://"], HTTPAdapter) and isinstance(
        session.adapters["https://"], HTTPAdapter
    )
    assert session.adapters["http://"].max_retries.total == total
    assert session.adapters["http://"].max_retries.backoff_factor == backoff_factor
    assert session.adapters["http://"].max_retries.status_forcelist == status_forcelist
    assert session.adapters["https://"].max_retries.total == total
    assert session.adapters["https://"].max_retries.backoff_factor == backoff_factor
    assert session.adapters["https://"].max_retries.status_forcelist == status_forcelist


@patch("operatorcert.utils.yaml.safe_load")
def test_get_repo_config(mock_yaml_load: MagicMock) -> None:
    mock_yaml_load.return_value = {"foo": "bar"}
    mock_open = mock.mock_open()
    with mock.patch("builtins.open", mock_open):
        result = utils.get_repo_config("foo")
        mock_yaml_load.assert_called_once_with(mock_open.return_value)
        assert result == {"foo": "bar"}


def test_run_command() -> None:
    result = utils.run_command(["echo", "foo"])
    assert result.stdout.decode("utf-8") == "foo\n"

    with pytest.raises(subprocess.CalledProcessError):
        utils.run_command(["false"])


@pytest.mark.parametrize(
    ["ocp", "expected"],
    [
        (
            {"data": [{"ocp_version": "4.13"}, {"ocp_version": "4.14"}]},
            ["4.13", "4.14"],
        ),
        ({"data": []}, []),
    ],
)
@patch("operatorcert.utils.requests")
def test_get_ocp_supported_versions(
    mock_get: MagicMock, ocp: Dict[str, List[Dict[str, str]]], expected: str
) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = ocp
    mock_get.get.return_value = mock_response
    assert utils.get_ocp_supported_versions("org", "v4.14") == expected

    mock_get.get.assert_called_once()


@patch("operatorcert.utils.requests.get")
def test_get_ocp_supported_versions_error(mock_get: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError(
        "404, GET request to fetch the indices failed"
    )
    mock_get.return_value = mock_response
    result = utils.get_ocp_supported_versions("org", "4.12")
    assert result is None
    mock_get.assert_called_once()


@patch("operatorcert.utils.subprocess")
def test_copy_images_to_destination(mock_subprocess: MagicMock) -> None:
    iib_response = [
        {
            "from_index": "quay.io/qwe/asd:v4.12",
            "index_image_resolved": "quay.io/qwe/asd@sha256:1234",
        }
    ]
    utils.copy_images_to_destination(
        iib_response, "quay.io/foo/bar", "-foo", "test.txt"
    )

    mock_subprocess.run.assert_called_once_with(
        [
            "skopeo",
            "copy",
            "--retry-times",
            "5",
            "docker://quay.io/qwe/asd@sha256:1234",
            "docker://quay.io/foo/bar:v4.12-foo",
            "--authfile",
            "test.txt",
        ],
        stdout=mock_subprocess.PIPE,
        stderr=mock_subprocess.PIPE,
        check=True,
    )
