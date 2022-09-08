from pathlib import Path
from unittest import mock
from unittest.mock import call, MagicMock

import pytest
import os

from operatorcert import utils
from operatorcert.utils import store_results


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
        call("example_name", "w"),
        call("other_name", "w"),
        call("third_name", "w"),
        call("none", "w"),
    ]


def test_set_client_keytab() -> None:
    assert utils.set_client_keytab("") is None

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
    session = utils.Session()
    utils.add_session_retries(
        session,
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    assert session.adapters["http://"].max_retries.total == total
    assert session.adapters["http://"].max_retries.backoff_factor == backoff_factor
    assert session.adapters["http://"].max_retries.status_forcelist == status_forcelist
    assert session.adapters["https://"].max_retries.total == total
    assert session.adapters["https://"].max_retries.backoff_factor == backoff_factor
    assert session.adapters["https://"].max_retries.status_forcelist == status_forcelist
