from pathlib import Path

from operatorcert import utils


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
