from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from operatorcert.entrypoints import static_tests
from operatorcert.operator_repo import Repo
from operatorcert.operator_repo.checks import Fail, Warn
from tests.utils import bundle_files, catalog_files, create_files


@pytest.mark.parametrize(
    "check_results, bundle, catalog_operators, expected",
    [
        pytest.param(
            [],
            "0.0.1",
            "v4.14/test-operator",
            {"passed": True, "outputs": []},
            id="No failures or warnings",
        ),
        pytest.param(
            [Warn("foo")],
            "0.0.1",
            "v4.14/test-operator",
            {
                "passed": True,
                "outputs": [
                    {"type": "warning", "message": "foo", "test_suite": "dummy_suite"}
                ],
            },
            id="One warning",
        ),
        pytest.param(
            [Fail("bar", check="baz")],
            "0.0.1",
            "v4.14/test-operator",
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
            id="One failure",
        ),
        pytest.param(
            [Warn("foo"), Fail("bar")],
            "0.0.1",
            "v4.14/test-operator",
            {
                "passed": False,
                "outputs": [
                    {"type": "warning", "message": "foo", "test_suite": "dummy_suite"},
                    {"type": "error", "message": "bar", "test_suite": "dummy_suite"},
                ],
            },
            id="One warning and one failure",
        ),
        pytest.param(
            [],
            "",
            "",
            {
                "passed": True,
                "outputs": [],
            },
            id="Removed operator",
        ),
        pytest.param(
            [],
            "0.0.1",
            "v4.12/test-operator",
            {
                "passed": True,
                "outputs": [],
            },
            id="Unknown catalog operator",
        ),
    ],
    indirect=False,
)
@patch("operatorcert.entrypoints.static_tests.run_suite")
def test_execute_checks(
    mock_run_suite: MagicMock,
    tmp_path: Any,
    bundle: str,
    catalog_operators: str,
    check_results: Any,
    expected: Any,
) -> None:
    operator_name = "test-operator"
    bundle_version = bundle
    affected_catalogs = "v4.14/test-operator"

    # Always create a an operator and catalog directory to have a valid repo
    create_files(
        tmp_path,
        bundle_files("operator_1", "0.0.1"),
        catalog_files("v4.15", "operator_1"),
    )

    if bundle:
        create_files(
            tmp_path,
            bundle_files(operator_name, "0.0.1"),
        )
    if catalog_operators:
        catalog, catalog_operator = catalog_operators.split("/")
        create_files(
            tmp_path,
            catalog_files(catalog, catalog_operator),
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
