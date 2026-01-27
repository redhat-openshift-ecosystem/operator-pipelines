from typing import Any
from unittest import mock
from unittest.mock import ANY, MagicMock, patch

import pytest
from operatorcert.entrypoints.preflight_result_filter import (
    COMMUNITY_ALLOWED_TESTS,
    main,
    parse_and_evaluate_results,
    setup_argparser,
)


@patch("operatorcert.entrypoints.preflight_result_filter.json.dump")
@patch("operatorcert.entrypoints.preflight_result_filter.parse_and_evaluate_results")
@patch("operatorcert.entrypoints.preflight_result_filter.OperatorRepo")
@patch("operatorcert.entrypoints.preflight_result_filter.setup_logger")
@patch("operatorcert.entrypoints.preflight_result_filter.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_operator_repo: MagicMock,
    mock_parse_and_evaluate_results: MagicMock,
    mock_json_dump: MagicMock,
) -> None:
    args = MagicMock()
    args.test_results = "some_file"
    args.output_file = "tmp/output.json"
    args.skip_tests = ["foo"]
    mock_setup_argparser.return_value.parse_args.return_value = args
    mock_operator_repo.return_value.config = {"organization": "community-operators"}
    mock_parse_and_evaluate_results.return_value = {"foo": "bar"}
    mock_open = mock.mock_open(read_data="{}")

    with mock.patch("builtins.open", mock_open):
        main()

    mock_parse_and_evaluate_results.assert_called_once_with(
        {}, "community-operators", ["foo"]
    )
    mock_json_dump.assert_called_once_with({"foo": "bar"}, ANY, indent=2)


@pytest.mark.parametrize(
    "test_results, organization, expected_tests",
    [
        pytest.param(
            {"results": {"failed": [{"name": "foo"}]}, "passed": False},
            "community-operators",
            {"results": {"failed": []}, "passed": True},
            id="failed - unrelated",
        ),
        pytest.param(
            {
                "results": {
                    "failed": [{"name": COMMUNITY_ALLOWED_TESTS[0]}, {"name": "foo"}]
                },
                "passed": False,
            },
            "community-operators",
            {
                "results": {"failed": [{"name": COMMUNITY_ALLOWED_TESTS[0]}]},
                "passed": False,
            },
            id="failed - community related",
        ),
        pytest.param(
            {
                "results": {
                    "failed": [{"name": COMMUNITY_ALLOWED_TESTS[0]}, {"name": "foo"}]
                },
                "passed": False,
            },
            "community-operators",
            {
                "results": {"failed": [{"name": COMMUNITY_ALLOWED_TESTS[0]}]},
                "passed": False,
            },
            id="failed - mixed",
        ),
        pytest.param(
            {
                "results": {
                    "passed": [{"name": COMMUNITY_ALLOWED_TESTS[0]}, {"name": "foo"}]
                },
                "passed": True,
            },
            "community-operators",
            {
                "results": {"passed": [{"name": COMMUNITY_ALLOWED_TESTS[0]}]},
                "passed": True,
            },
            id="passed - mixed",
        ),
        pytest.param(
            {
                "results": {
                    "passed": [{"name": COMMUNITY_ALLOWED_TESTS[0]}],
                    "failed": [{"name": "foo"}],
                },
                "passed": False,
            },
            "community-operators",
            {
                "results": {
                    "passed": [{"name": COMMUNITY_ALLOWED_TESTS[0]}],
                    "failed": [],
                },
                "passed": True,
            },
            id="passed and failed - mixed",
        ),
        pytest.param(
            {
                "results": {
                    "passed": [{"name": COMMUNITY_ALLOWED_TESTS[0]}],
                    "failed": [{"name": "foo"}, {"name": COMMUNITY_ALLOWED_TESTS[1]}],
                },
                "passed": False,
            },
            "certified-operators",
            {
                "results": {
                    "passed": [{"name": COMMUNITY_ALLOWED_TESTS[0]}],
                    "failed": [{"name": "foo"}, {"name": COMMUNITY_ALLOWED_TESTS[1]}],
                },
                "passed": False,
            },
            id="certified - failed",
        ),
    ],
)
def test_parse_and_evaluate_results(
    test_results: Any, organization: str, expected_tests: Any
) -> None:
    output = parse_and_evaluate_results(test_results, organization)

    assert output == expected_tests


def test_setup_argparser() -> None:
    assert setup_argparser() is not None
