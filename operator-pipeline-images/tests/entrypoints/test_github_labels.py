from typing import Any, List
from unittest import mock
from unittest.mock import MagicMock, call, patch

import pytest
from operatorcert.entrypoints.github_labels import (
    add_labels_to_pull_request,
    add_or_remove_labels,
    main,
    remove_labels_from_pull_request,
    setup_argparser,
)


@patch("operatorcert.entrypoints.github_labels.add_or_remove_labels")
@patch("operatorcert.entrypoints.github_labels.Github")
@patch("operatorcert.entrypoints.github_labels.setup_logger")
@patch("operatorcert.entrypoints.github_labels.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_github: MagicMock,
    mock_add_or_remove_labels: MagicMock,
    monkeypatch: Any,
) -> None:
    args = MagicMock()
    args.add_labels = ["label1"]
    args.remove_labels = ["label2"]
    args.remove_matching_namespace_labels = True
    args.pull_request_url = "https://github.com/foo/bar/pull/123"
    mock_setup_argparser.return_value.parse_args.return_value = args

    monkeypatch.setenv("GITHUB_TOKEN", "foo_api_token")
    main()

    mock_add_or_remove_labels.assert_called_once_with(
        mock_github(),
        "https://github.com/foo/bar/pull/123",
        ["label1"],
        ["label2"],
        True,
    )


@pytest.mark.parametrize(
    "current_labels, add_label, remove_label, remove_namespaced, expected_add, expected_remove",
    [
        pytest.param([], ["label1"], [], False, ["label1"], [], id="add label"),
        pytest.param(
            ["label1"], ["label1"], [], False, [], [], id="add existing label"
        ),
        pytest.param(
            ["label1"], [], ["label1"], False, [], ["label1"], id="remove label"
        ),
        pytest.param([], [], ["label1"], False, [], [], id="remove non-existing label"),
        pytest.param(
            ["namespace/label1", "namespace/label2", "existing_label", "bar"],
            ["namespace/new"],
            [],
            False,
            ["namespace/new"],
            [],
            id="add namespaced label",
        ),
        pytest.param(
            ["namespace/label1", "namespace/label2", "existing_label", "bar"],
            ["namespace/new"],
            [],
            True,
            ["namespace/new"],
            ["namespace/label2", "namespace/label1"],
            id="add namespaced label and remove existing",
        ),
        pytest.param(
            ["namespace/label1", "namespace/label2", "existing_label", "bar"],
            ["namespace/label1"],
            [],
            True,
            [],
            ["namespace/label2"],
            id="remove namespaced label and keep existing",
        ),
        pytest.param(
            ["namespace/label1", "namespace/label2", "existing_label", "bar"],
            ["namespace/new"],
            ["bar"],
            True,
            ["namespace/new"],
            ["bar", "namespace/label2", "namespace/label1"],
            id="add namespaced label and remove existing and non-namespaced",
        ),
    ],
)
@patch("operatorcert.entrypoints.github_labels.remove_labels_from_pull_request")
@patch("operatorcert.entrypoints.github_labels.add_labels_to_pull_request")
def test_add_or_remove_labels(
    mock_add_label: MagicMock,
    mock_remove_label: MagicMock,
    current_labels: List[Any],
    add_label: List[str],
    remove_label: List[str],
    remove_namespaced: bool,
    expected_add: List[str],
    expected_remove: List[str],
) -> None:
    mock_github = MagicMock()

    mock_current_labels = []
    for label in current_labels:
        # The name property can't be set directly on the MagicMock
        mock_label = MagicMock()
        mock_label.name = label
        mock_current_labels.append(mock_label)

    print(current_labels)

    mock_github.get_repo.return_value.get_pull.return_value.get_labels.return_value = (
        mock_current_labels
    )

    add_or_remove_labels(
        mock_github,
        "https://github.com/foo/bar/pull/10",
        add_label,
        remove_label,
        remove_namespaced,
    )

    mock_add_label.assert_called_once_with(
        mock_github.get_repo().get_pull(), expected_add
    )
    mock_remove_label.assert_called_once_with(
        mock_github.get_repo().get_pull(), mock.ANY
    )
    # The order of the labels is not guaranteed, so we need to sort them
    sorted(mock_remove_label.call_args_list[0][0][1]) == sorted(expected_remove)


def test_add_labels_to_pull_request() -> None:
    mock_pull_request = MagicMock()
    add_labels_to_pull_request(mock_pull_request, ["label1", "label2"])

    mock_pull_request.add_to_labels.assert_has_calls([call("label1"), call("label2")])


def test_remove_labels_from_pull_request() -> None:
    mock_pull_request = MagicMock()
    remove_labels_from_pull_request(mock_pull_request, ["label1", "label2"])

    mock_pull_request.remove_from_labels.assert_has_calls(
        [call("label1"), call("label2")]
    )


def test_setup_argparser() -> None:
    assert setup_argparser() is not None
