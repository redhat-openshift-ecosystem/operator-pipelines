from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from _pytest.capture import CaptureFixture
from operatorcert.operator_repo import Bundle, Operator, Repo
from operatorcert.operator_repo.checks import CheckResult
from operatorcert.operator_repo.cli import _get_repo, main, parse_target


def test_cli_parse_target(mock_repo: Repo) -> None:
    assert parse_target(mock_repo, "hello") == mock_repo.operator("hello")
    assert parse_target(mock_repo, "world/0.0.1") == mock_repo.operator("world").bundle(
        "0.0.1"
    )


def test_cli_list(mock_repo: Repo, capsys: CaptureFixture[str]) -> None:
    with patch("sys.argv", ["optool", "-r", str(mock_repo.root), "list", "hello"]):
        main()
    captured = capsys.readouterr()
    assert "hello/0.0.1" in captured.out
    assert "hello/0.0.2" in captured.out
    assert "v4.17/hello" in captured.out
    assert "v4.18/hello" in captured.out


def test_cli_list_repo(mock_repo: Repo, capsys: CaptureFixture[str]) -> None:
    with patch("sys.argv", ["optool", "-r", str(mock_repo.root), "list"]):
        main()
    captured = capsys.readouterr()
    assert "hello" in captured.out
    assert "world" in captured.out


def test_cli_list_bundle(mock_repo: Repo, capsys: CaptureFixture[str]) -> None:
    with patch(
        "sys.argv", ["optool", "-r", str(mock_repo.root), "list", "hello/0.0.1"]
    ):
        main()
    captured = capsys.readouterr()
    assert "hello/0.0.1" in captured.out
    assert "hello/0.0.2" not in captured.out


def test_cli_list_recursive(mock_repo: Repo, capsys: CaptureFixture[str]) -> None:
    with patch("sys.argv", ["optool", "-r", str(mock_repo.root), "list", "-R"]):
        main()
    captured = capsys.readouterr()
    assert "hello/0.0.1" in captured.out
    assert "hello/0.0.2" in captured.out
    assert "world/0.0.1" in captured.out
    assert "world/0.0.2" in captured.out


def test_cli_check(mock_repo: Repo, capsys: CaptureFixture[str]) -> None:
    with patch("sys.argv", ["optool", "-r", str(mock_repo.root), "check", "world"]):
        main()
    captured = capsys.readouterr()
    assert (
        "Operator's 'ci.yaml' contains invalid data which does not comply"
        in captured.out
    )


def test_cli_check_recursive(mock_repo: Repo, capsys: CaptureFixture[str]) -> None:
    with patch("sys.argv", ["optool", "-r", str(mock_repo.root), "check", "-R"]):
        main()
    captured = capsys.readouterr()
    assert "check_operator_name(Bundle(world/0.0.2)): Operator name from "
    "annotations.yaml (fake-incorect-name) does not match" in captured.out


def test_cli_check_operator_recursive(
    mock_repo: Repo, capsys: CaptureFixture[str]
) -> None:
    with patch(
        "sys.argv", ["optool", "-r", str(mock_repo.root), "check", "-R", "world"]
    ):
        main()
    captured = capsys.readouterr()
    assert (
        "check_operator_name(Bundle(world/0.0.2)): Operator name from "
        "annotations.yaml (fake-incorect-name) does not match" in captured.out
    )


@patch("operatorcert.operator_repo.cli.get_checks")
def test_cli_check_list(mock_checks: MagicMock, capsys: CaptureFixture[str]) -> None:
    def check_foo(_: Operator) -> Iterator[CheckResult]:
        """This is the check_foo description"""
        raise StopIteration

    def check_bar(_: Bundle) -> Iterator[CheckResult]:
        """This is the check_bar description"""
        raise StopIteration

    mock_checks.return_value = {"operator": [check_foo], "bundle": [check_bar]}
    with patch("sys.argv", ["optool", "check", "--list"]):
        main()
    captured = capsys.readouterr()
    assert "This is the check_foo description" in captured.out
    assert "This is the check_bar description" in captured.out


@patch("operatorcert.operator_repo.cli.Path.cwd")
def test_cli_get_repo(mock_cwd: MagicMock, mock_repo: Repo) -> None:
    mock_cwd.return_value = mock_repo.root
    assert _get_repo() == mock_repo


@patch("operatorcert.operator_repo.cli.Path.cwd")
def test_cli_get_repo_invalid(
    mock_cwd: MagicMock, tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    mock_cwd.return_value = tmp_path
    with pytest.raises(SystemExit):
        _ = _get_repo()
    captured = capsys.readouterr()
    assert "is not a valid operator repository" in captured.out


def test_cli_help(capsys: CaptureFixture[str]) -> None:
    with patch("sys.argv", ["optool"]):
        main()
    captured = capsys.readouterr()
    assert "usage: optool" in captured.out
