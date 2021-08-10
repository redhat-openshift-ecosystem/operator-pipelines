from pathlib import Path
from unittest import mock
from unittest.mock import call, MagicMock

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
    results = {"example_name": "example_value", "other_name": "other_value", "none": None}
    mock_open = mock.mock_open()
    with mock.patch("builtins.open", mock_open):
        store_results(results)

    assert mock_open.call_count == 3
    assert mock_open.call_args_list == [
        call("example_name", "w"),
        call("other_name", "w"),
        call("none", "w"),
    ]
