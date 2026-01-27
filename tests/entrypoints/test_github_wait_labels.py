from typing import Any, List
from unittest import mock
from unittest.mock import MagicMock, call, patch

import pytest
from github.Repository import Repository
from github import GithubException

from operatorcert.entrypoints.github_wait_labels import (
    main,
    WaitCondition,
    WaitType,
    get_pr_labels,
    setup_argparser,
    wait_on_pr_labels,
)


def test_setup_argparser() -> None:
    assert setup_argparser() is not None


@patch("operatorcert.entrypoints.github_wait_labels.wait_on_pr_labels")
@patch("operatorcert.entrypoints.github_wait_labels.Github.get_repo")
@patch("operatorcert.entrypoints.github_wait_labels.setup_logger")
def test_main(
    mock_setup_logger: MagicMock,
    mock_github_get_repo: MagicMock,
    mock_wait_on_pr_labels: MagicMock,
    monkeypatch: Any,
) -> None:
    mock_repo = MagicMock()
    mock_github_get_repo.return_value = mock_repo()
    mock_wait_on_pr_labels.return_value = True

    monkeypatch.setenv("GITHUB_TOKEN", "foo_api_token")

    args = [
        "github-wait-labels",
        "--github-host-url",
        "https://api.example.com",
        "--pull-request-url",
        "https://example.com/namespace/repo/pull/999",
        "--any",
        r"ocp/4\.10/(pass|fail)",
        "--any",
        r"ocp/4\.11/(pass|fail)",
        "--none",
        r"do-not-merge",
        "--poll-interval",
        "15",
        "--timeout",
        "1000",
        "--verbose",
    ]

    with patch("sys.argv", args):
        assert main() == 0

    # want to test with __eq__ here to avoid mocking
    assert mock_wait_on_pr_labels.call_args[0][2] == [
        WaitCondition(WaitType.WAIT_ANY, r"ocp/4\.10/(pass|fail)"),
        WaitCondition(WaitType.WAIT_ANY, r"ocp/4\.11/(pass|fail)"),
        WaitCondition(WaitType.WAIT_NONE, r"do-not-merge"),
    ]

    assert mock_wait_on_pr_labels.call_args[0][1] == 999
    assert mock_wait_on_pr_labels.call_args[0][3] == 1000
    assert mock_wait_on_pr_labels.call_args[0][4] == 15


@patch("operatorcert.entrypoints.github_wait_labels.wait_on_pr_labels")
@patch("operatorcert.entrypoints.github_wait_labels.Github.get_repo")
@patch("operatorcert.entrypoints.github_wait_labels.setup_logger")
def test_main_error(
    mock_setup_logger: MagicMock,
    mock_github_get_repo: MagicMock,
    mock_wait_on_pr_labels: MagicMock,
    monkeypatch: Any,
) -> None:
    mock_repo = MagicMock()
    mock_github_get_repo.return_value = mock_repo()

    monkeypatch.setenv("GITHUB_TOKEN", "foo_api_token")
    mock_wait_on_pr_labels.return_value = False

    args = [
        "github-wait-labels",
        "--pull-request-url",
        "https://example.com/namespace/repo/pull/999",
    ]

    with patch("sys.argv", args):
        assert main() == 1


@patch("operatorcert.entrypoints.github_wait_labels.wait_on_pr_labels")
@patch("operatorcert.entrypoints.github_wait_labels.Github.get_repo")
@patch("operatorcert.entrypoints.github_wait_labels.setup_logger")
def test_main_get_repo_exception(
    mock_setup_logger: MagicMock,
    mock_github_get_repo: MagicMock,
    mock_wait_on_pr_labels: MagicMock,
    monkeypatch: Any,
) -> None:
    mock_repo = MagicMock()
    mock_github_get_repo.side_effect = GithubException(0, "err", None)

    monkeypatch.setenv("GITHUB_TOKEN", "foo_api_token")
    mock_wait_on_pr_labels.return_value = False

    args = [
        "github-wait-labels",
        "--pull-request-url",
        "https://example.com/namespace/repo/pull/999",
    ]

    with patch("sys.argv", args):
        assert main() == 2


def test_get_pr_labels() -> None:
    mock_repo = MagicMock()
    labels = [MagicMock(), MagicMock()]
    for mock_label, label_name in zip(labels, ["label1", "label2"]):
        mock_label.name = label_name

    mock_pr = MagicMock()
    mock_pr.labels = labels
    mock_repo.get_pull.return_value = mock_pr

    assert get_pr_labels(mock_repo, 0) == ["label1", "label2"]


def test_get_wait_conditions() -> None:
    args = MagicMock()
    args.any = ["one", "two"]
    args.none = ["three"]

    assert WaitCondition.get_wait_conditions(args) == [
        WaitCondition(WaitType.WAIT_ANY, "one"),
        WaitCondition(WaitType.WAIT_ANY, "two"),
        WaitCondition(WaitType.WAIT_NONE, "three"),
    ]


@pytest.mark.parametrize(
    ["wait_type", "regexp", "labels", "result"],
    [
        (WaitType.WAIT_ANY, "test", ["test"], True),
        (WaitType.WAIT_ANY, "test", ["one", "another-one", "hello", "test"], True),
        (WaitType.WAIT_ANY, "test", ["test", "more-labels"], True),
        (WaitType.WAIT_ANY, "test", [], False),
        (WaitType.WAIT_ANY, "t..t", ["test"], True),
        (WaitType.WAIT_NONE, "test", ["test"], False),
        (WaitType.WAIT_NONE, "test", ["more-labels"], True),
        (WaitType.WAIT_NONE, "test", ["one", "two", "three"], True),
        (WaitType.WAIT_NONE, "test", ["one", "two", "test"], False),
        (None, "test", ["test"], False),
    ],
)
def test_condition_holds(
    wait_type: WaitType, regexp: str, labels: list[str], result: bool
) -> None:
    condition = WaitCondition(wait_type, regexp)
    assert condition.holds(labels) == result


@pytest.mark.parametrize(
    ["pr_labels_sequence", "wait_conditions"],
    [
        pytest.param(
            [["label_one", "label_two"]],
            [WaitCondition(WaitType.WAIT_ANY, ".*two")],
            id="any one label",
        ),
        pytest.param(
            [["label_one"], ["label_one", "label_two"]],
            [WaitCondition(WaitType.WAIT_ANY, ".*two")],
            id="any one label repoll",
        ),
        pytest.param(
            [["label_one", "label_two"]],
            [
                WaitCondition(WaitType.WAIT_ANY, "label_two"),
                WaitCondition(WaitType.WAIT_ANY, "label_one"),
            ],
            id="any two labels",
        ),
        pytest.param(
            [["label_one"], ["label_one", "label_two"]],
            [
                WaitCondition(WaitType.WAIT_ANY, "label_two"),
                WaitCondition(WaitType.WAIT_ANY, "label_one"),
            ],
            id="any two labels repoll",
        ),
        pytest.param(
            [["label_one", "label_two"]],
            [WaitCondition(WaitType.WAIT_NONE, "three")],
            id="none one label",
        ),
        pytest.param(
            [["label_one", "label_two"], ["label_one"]],
            [WaitCondition(WaitType.WAIT_NONE, "label_two")],
            id="none one label repoll",
        ),
        pytest.param(
            [["label_one", "label_two"]],
            [
                WaitCondition(WaitType.WAIT_NONE, "three"),
                WaitCondition(WaitType.WAIT_NONE, "four"),
            ],
            id="none two labels",
        ),
        pytest.param(
            [["label_one", "label_two"], ["label_two"]],
            [
                WaitCondition(WaitType.WAIT_NONE, "label_one"),
                WaitCondition(WaitType.WAIT_NONE, "label_three"),
            ],
            id="none two labels repoll",
        ),
        pytest.param(
            [["label_one", "label_two"]],
            [
                WaitCondition(WaitType.WAIT_ANY, "label_one"),
                WaitCondition(WaitType.WAIT_NONE, "label_three"),
            ],
            id="mixed conditions",
        ),
        pytest.param(
            [["label_one", "label_two"], ["label_one"]],
            [
                WaitCondition(WaitType.WAIT_ANY, "label_one"),
                WaitCondition(WaitType.WAIT_NONE, "label_two"),
            ],
            id="mixed conditions repoll",
        ),
    ],
)
@patch("operatorcert.entrypoints.github_wait_labels.get_pr_labels")
def test_wait_on_pr_labels_success(
    mock_get_pr_labels: MagicMock,
    pr_labels_sequence: list[list[str]],
    wait_conditions: list[WaitCondition],
    capsys: Any,
) -> None:
    mock_get_pr_labels.side_effect = pr_labels_sequence
    assert wait_on_pr_labels(MagicMock(), 1, wait_conditions, 5, 0.1)

    captured_stdout, _ = capsys.readouterr()
    assert captured_stdout == str.join("\n", pr_labels_sequence[-1]) + "\n"


@pytest.mark.parametrize(
    ["pr_labels", "wait_conditions"],
    [
        pytest.param(["label"], [WaitCondition(WaitType.WAIT_ANY, "test")]),
        pytest.param(["label"], [WaitCondition(WaitType.WAIT_NONE, "label")]),
    ],
)
@patch("operatorcert.entrypoints.github_wait_labels.get_pr_labels")
def test_wait_on_pr_labels_timeout(
    mock_get_pr_labels: MagicMock,
    pr_labels: list[str],
    wait_conditions: list[WaitCondition],
) -> None:
    mock_get_pr_labels.return_value = pr_labels
    assert not wait_on_pr_labels(MagicMock(), 1, wait_conditions, 1, 0.1)


@patch("operatorcert.entrypoints.github_wait_labels.sys.exit")
def test_get_pr_labels_exception(mock_exit: MagicMock) -> None:
    mock_repo = MagicMock()
    mock_repo.get_pull.side_effect = GithubException(0, "err", None)

    mock_exit.side_effect = Exception("End program at exit")

    with pytest.raises((GithubException, Exception)):
        get_pr_labels(mock_repo, 0)

    mock_exit.assert_called_once_with(1)
