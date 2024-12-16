from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from operator_repo import Repo
from operator_repo.checks import Fail, Warn
from operatorcert.entrypoints import static_tests
from tests.utils import bundle_files, catalog_files, create_files


@pytest.mark.parametrize(
    "check_results, bundle, expected",
    [
        (
            [],
            "0.0.1",
            {"passed": True, "outputs": []},
        ),
        (
            [Warn("foo")],
            "0.0.1",
            {
                "passed": True,
                "outputs": [
                    {"type": "warning", "message": "foo", "test_suite": "dummy_suite"}
                ],
            },
        ),
        (
            [Fail("bar", check="baz")],
            "",
            {
                "passed": False,
                "outputs": [
                    {
                        "type": "error",
                        "message": "bar",
                        "check": "baz",
                        "test_suite": "dummy_suite",
                    }
                ],
            },
        ),
        (
            [Warn("foo"), Fail("bar")],
            "0.0.1",
            {
                "passed": False,
                "outputs": [
                    {"type": "warning", "message": "foo", "test_suite": "dummy_suite"},
                    {"type": "error", "message": "bar", "test_suite": "dummy_suite"},
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
def test_execute_checks(
    mock_run_suite: MagicMock,
    tmp_path: Any,
    bundle: str,
    check_results: Any,
    expected: Any,
) -> None:
    operator_name = "test-operator"
    bundle_version = bundle
    affected_catalogs = "v4.14/test-operator"
    create_files(
        tmp_path,
        bundle_files(operator_name, "0.0.1"),
        catalog_files("v4.14", "test-operator"),
    )

    repo = Repo(tmp_path)

    mock_run_suite.return_value = iter(check_results)
    result = static_tests.execute_checks(
        str(repo.root),
        operator_name,
        bundle_version,
        affected_catalogs,
        ["dummy_suite"],
    )
    assert result == expected


@patch("operatorcert.entrypoints.static_tests.execute_checks")
@patch("operatorcert.entrypoints.static_tests.setup_logger")
def test_static_tests_main(
    mock_logger: MagicMock, mock_execute_checks: MagicMock, capsys: Any, tmpdir: Any
) -> None:
    args = [
        "static-tests",
        "--repo-path=/tmp/repo",
        "test-operator",
        "0.0.1",
        ["v4.14/test-operator"],
    ]
    mock_execute_checks.return_value = {"foo": ["bar"]}
    with patch("sys.argv", args):
        static_tests.main()
    mock_execute_checks.assert_called_once_with(
        "/tmp/repo",
        "test-operator",
        "0.0.1",
        ["v4.14/test-operator"],
        ["operatorcert.static_tests.community", "operatorcert.static_tests.common"],
        [],
    )
    assert capsys.readouterr().out.strip() == '{"foo": ["bar"]}'
    mock_logger.assert_called_once_with(level="INFO")

    mock_logger.reset_mock()
    mock_execute_checks.reset_mock()

    out_file = tmpdir / "out.json"
    out_file_name = str(out_file)
    args = [
        "static-tests",
        "--repo-path=/tmp/other_repo",
        "--skip-tests=check_123,check_456",
        "other-test-operator",
        "0.0.2",
        ["v4.14/test-operator"],
        "--suites=other_suite",
        f"--output-file={out_file_name}",
        "--verbose",
    ]
    mock_execute_checks.return_value = {"bar": ["baz"]}
    with patch("sys.argv", args):
        static_tests.main()
    mock_execute_checks.assert_called_once_with(
        "/tmp/other_repo",
        "other-test-operator",
        "0.0.2",
        ["v4.14/test-operator"],
        ["other_suite"],
        ["check_123", "check_456"],
    )
    assert out_file.read().strip() == '{"bar": ["baz"]}'
    mock_logger.assert_called_once_with(level="DEBUG")
