from typing import Any
from unittest.mock import ANY, MagicMock, patch

import pytest

from operatorcert.entrypoints import apply_test_waivers
from operatorcert.workflow_exceptions import WorkflowException


def test_setup_argparser() -> None:
    assert apply_test_waivers.setup_argparser() is not None


def test_can_ignore_test() -> None:
    assert (
        apply_test_waivers.can_ignore_test(
            {"name": "test1", "ignore_operators": ["^foo.*"]}, "foo"
        )
        is True
    )
    assert (
        apply_test_waivers.can_ignore_test(
            {"name": "test2", "ignore_operators": ["^foo.*", "^bar.*"]}, "foo"
        )
        is True
    )
    assert (
        apply_test_waivers.can_ignore_test(
            {"name": "test3", "ignore_operators": ["^foo.*"]}, "bar"
        )
        is False
    )


@pytest.mark.parametrize(
    ["exceptions", "operator_name", "expected_given_exceptions"],
    [
        pytest.param(
            {"duplicate_name": ["^foo_operator"]},
            "foo_operator_1",
            [WorkflowException.DUPLICATE_NAME],
            id="match duplicate name",
        ),
        pytest.param({"duplicate_name": ["^foo_operator"]}, "bar", [], id="no match"),
        pytest.param({}, "spam", [], id="no exceptions configured"),
    ],
)
def test_has_exceptions(
    exceptions: dict[str, list[str]],
    operator_name: str,
    expected_given_exceptions: list[WorkflowException],
) -> None:
    assert (
        apply_test_waivers.has_exceptions(exceptions, operator_name)
        == expected_given_exceptions
    )


@patch("operatorcert.entrypoints.apply_test_waivers.add_or_remove_labels")
@patch("operatorcert.entrypoints.apply_test_waivers.can_ignore_test")
@patch("operatorcert.entrypoints.apply_test_waivers.get_repo_config")
def test_configure_test_suite(
    mock_repo_config: MagicMock, mock_can_ignore_test: MagicMock, mock_labels: MagicMock
) -> None:
    mock_repo_config.return_value = {
        "tests": [
            {"name": "test1", "ignore_operators": ["foo"]},
            {"name": "test2", "ignore_operators": ["bar"]},
        ]
    }
    mock_can_ignore_test.side_effect = [True, False]
    mock_github = MagicMock()
    mock_args = MagicMock()
    apply_test_waivers.configure_test_suite(mock_args, mock_github)

    mock_labels.assert_called_once_with(ANY, ANY, ["tests/skip/test1"], [], True)


@patch("operatorcert.entrypoints.apply_test_waivers.configure_test_suite")
@patch("operatorcert.entrypoints.apply_test_waivers.Github")
@patch("operatorcert.entrypoints.apply_test_waivers.setup_logger")
@patch("operatorcert.entrypoints.apply_test_waivers.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_github: MagicMock,
    mock_configure_test_suite: MagicMock,
    monkeypatch: Any,
) -> None:
    args = MagicMock()
    mock_setup_argparser.return_value.parse_args.return_value = args

    monkeypatch.setenv("GITHUB_TOKEN", "foo_api_token")
    apply_test_waivers.main()

    mock_configure_test_suite.assert_called_once_with(args, mock_github())
