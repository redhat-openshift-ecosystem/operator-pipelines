from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from operator_repo import Repo
from operator_repo.checks import Fail, Warn
from operatorcert.entrypoints import static_tests
from tests.utils import bundle_files, create_files


@pytest.mark.parametrize(
    "check_results, expected",
    [
        (
            [],
            {"passed": True, "outputs": []},
        ),
        (
            [Warn("foo")],
            {
                "passed": True,
                "outputs": [{"type": "warning", "message": "foo"}],
            },
        ),
        (
            [Fail("bar", check="baz")],
            {
                "passed": False,
                "outputs": [{"type": "error", "message": "bar", "check": "baz"}],
            },
        ),
        (
            [Warn("foo"), Fail("bar")],
            {
                "passed": False,
                "outputs": [
                    {"type": "warning", "message": "foo"},
                    {"type": "error", "message": "bar"},
                ],
            },
        ),
    ],
    indirect=False,
    ids=[
        "No failures or warnings",
        "One warning",
        "One failure",
        "One warning and one failure",
    ],
)
@patch("operatorcert.entrypoints.static_tests.run_suite")
def test_check_bundle(
    mock_run_suite: MagicMock, tmp_path: Any, check_results: Any, expected: Any
) -> None:
    operator_name = "test-operator"
    bundle_version = "0.0.1"
    create_files(tmp_path, bundle_files(operator_name, bundle_version))

    repo = Repo(tmp_path)

    mock_run_suite.return_value = iter(check_results)
    result = static_tests.check_bundle(
        str(repo.root), operator_name, bundle_version, "dummy_suite"
    )
    assert result == expected


@patch("operatorcert.entrypoints.static_tests.check_bundle")
@patch("operatorcert.entrypoints.static_tests.setup_logger")
def test_static_tests_main(
    mock_logger: MagicMock, mock_check_bundle: MagicMock, capsys: Any, tmpdir: Any
) -> None:
    args = [
        "static-tests",
        "--repo-path=/tmp/repo",
        "test-operator",
        "0.0.1",
    ]
    mock_check_bundle.return_value = {"foo": ["bar"]}
    with patch("sys.argv", args):
        static_tests.main()
    mock_check_bundle.assert_called_once_with(
        "/tmp/repo", "test-operator", "0.0.1", "operatorcert.static_tests.community"
    )
    assert capsys.readouterr().out.strip() == '{"foo": ["bar"]}'
    mock_logger.assert_called_once_with(level="INFO")

    mock_logger.reset_mock()
    mock_check_bundle.reset_mock()

    out_file = tmpdir / "out.json"
    out_file_name = str(out_file)
    args = [
        "static-tests",
        "--repo-path=/tmp/other_repo",
        "other-test-operator",
        "0.0.2",
        "--suite=other_suite",
        f"--output-file={out_file_name}",
        "--verbose",
    ]
    mock_check_bundle.return_value = {"bar": ["baz"]}
    with patch("sys.argv", args):
        static_tests.main()
    mock_check_bundle.assert_called_once_with(
        "/tmp/other_repo", "other-test-operator", "0.0.2", "other_suite"
    )
    assert out_file.read().strip() == '{"bar": ["baz"]}'
    mock_logger.assert_called_once_with(level="DEBUG")
