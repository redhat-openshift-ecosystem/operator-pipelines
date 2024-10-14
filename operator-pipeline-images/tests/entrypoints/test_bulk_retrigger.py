from unittest.mock import patch, MagicMock, ANY, call
import logging
import pytest
from pathlib import Path
from typing import Any, Optional, Iterator

from operatorcert.entrypoints.bulk_retrigger import (
    parse_args,
    setup_logging,
    bulk_retrigger,
    retrigger_pipeline_for_pr,
    wait_for_all_labels,
    wait_for_any_label,
    parse_repo_name,
    MissingToken,
    InvalidRepoName,
    pr_numbers_from_csv,
    CSVNotFound,
)


def mock_label(name: str) -> MagicMock:
    label = MagicMock()
    label.name = name
    return label


def test_parse_args() -> None:
    args = [
        "bulk-retrigger",
        "--pipeline",
        "release",
        "--csv-delimiter",
        ";",
        "--pr-column",
        "1",
        "--verbose",
        "namespace/reponame",
        "file.csv",
    ]
    with patch("sys.argv", args):
        result = parse_args()
        assert result.pipeline == "release"
        assert result.csv_delimiter == ";"
        assert result.pr_column == 1
        assert result.verbose == True
        assert result.repo == "namespace/reponame"
        assert result.csv == Path("file.csv")


@patch("operatorcert.entrypoints.bulk_retrigger.logging.basicConfig")
def test_setup_logging(mock_basicconfig: MagicMock) -> None:
    setup_logging(True)
    mock_basicconfig.assert_called_once_with(format=ANY, level=logging.DEBUG)


@pytest.mark.parametrize(
    [
        "token",
        "name",
        "repo",
    ],
    [
        pytest.param(
            "secret",
            "foo/bar",
            "foo/bar",
            id="namespace/repo",
        ),
        pytest.param(
            "secret",
            "https://github.com/foo/bar",
            "foo/bar",
            id="full url",
        ),
        pytest.param(
            "",
            "foo/bar",
            MissingToken,
            id="missing token",
        ),
        pytest.param(
            "secret",
            "https://gitlab.com/foo/bar",
            InvalidRepoName,
            id="invalid repo name",
        ),
    ],
)
@patch("operatorcert.entrypoints.bulk_retrigger.Github")
@patch("operatorcert.entrypoints.bulk_retrigger.Auth.Token")
def test_parse_repo_name(
    mock_auth_token: MagicMock,
    mock_github: MagicMock,
    token: str,
    name: str,
    repo: str | type,
    monkeypatch: Any,
) -> None:
    gh = MagicMock()
    mock_github.return_value = gh
    mock_auth_token.return_value = MagicMock()
    gh.get_repo = MagicMock()
    gh.get_repo.return_value = MagicMock()

    if token:
        monkeypatch.setenv("GITHUB_TOKEN", token)
    else:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    if isinstance(repo, type):
        with pytest.raises(repo):
            parse_repo_name(name)
    else:
        assert parse_repo_name(name) == gh.get_repo.return_value
        mock_auth_token.assert_called_with(token)
        gh.get_repo.assert_called_with(repo)


@pytest.mark.parametrize(
    ["body", "delimiter", "column", "result"],
    [
        pytest.param(
            "1\n",
            ",",
            0,
            [1],
            id="single column, single row",
        ),
        pytest.param(
            None,
            ",",
            0,
            CSVNotFound,
            id="missing CSV",
        ),
        pytest.param(
            "one;1\ntwo;2\nthree;3\n",
            ";",
            1,
            [1, 2, 3],
            id="two columns, three rows",
        ),
        pytest.param(
            "one,1\ntwo,foo\nthree,3\n",
            ",",
            1,
            [1, ValueError, 3],
            id="invalid pr id",
        ),
    ],
)
def test_pr_numbers_from_csv(
    body: Optional[str],
    delimiter: str,
    column: int,
    result: list[int | Exception] | type,
    tmpdir: Path,
) -> None:
    csv_file = tmpdir / "test.csv"
    if body:
        csv_file.write_text(body, encoding="utf-8")
    if isinstance(result, type):
        with pytest.raises(result):
            list(pr_numbers_from_csv(csv_file, delimiter, column))
    else:
        prs = list(pr_numbers_from_csv(csv_file, delimiter, column))
        assert len(prs) == len(result)
        for actual, expected in zip(prs, result):
            if isinstance(expected, type):
                assert isinstance(actual, expected)
            else:
                assert actual == expected


@pytest.mark.parametrize(
    [
        "pipeline",
        "prs",
        "trigger_results",
        "result",
    ],
    [
        pytest.param(
            "hosted",
            [1, 2, 3],
            ["pass", "pass", "pass"],
            0,
            id="success",
        ),
        pytest.param(
            "hosted",
            [1, 2, 3],
            ["fail", "pass", "timeout"],
            2,
            id="some pipeline failures",
        ),
        pytest.param(
            "release",
            [1, 2, 3],
            ["pass", Exception(), "pass"],
            1,
            id="some errors",
        ),
        pytest.param(
            "release",
            [1, Exception(), 3],
            ["pass", "pass"],
            1,
            id="invalid pr number",
        ),
    ],
)
@patch("operatorcert.entrypoints.bulk_retrigger.retrigger_pipeline_for_pr")
def test_bulk_retrigger(
    mock_retrigger_pr: MagicMock,
    pipeline: str,
    prs: Iterator[int | Exception],
    trigger_results: list[str | Exception],
    result: int,
) -> None:
    mock_retrigger_pr.side_effect = trigger_results
    repo = MagicMock()
    assert bulk_retrigger(repo, pipeline, prs, 10) == result
    mock_retrigger_pr.assert_has_calls(
        [call(repo, x, pipeline, 10) for x in prs if not isinstance(x, Exception)]
    )


@pytest.mark.parametrize(
    [
        "pipeline",
        "pr",
        "initial_labels",
        "wait_all_result",
        "wait_any_result",
        "final_labels",
        "result",
    ],
    [
        pytest.param(
            "hosted",
            1,
            [],
            True,
            True,
            ["operator-hosted-pipeline/passed"],
            "pass",
            id="no initial labels; pass",
        ),
        pytest.param(
            "hosted",
            1,
            ["operator-hosted-pipeline/started"],
            None,
            None,
            [],
            "skipped",
            id="already running",
        ),
        pytest.param(
            "hosted",
            1,
            [],
            True,
            True,
            ["operator-hosted-pipeline/failed"],
            "fail",
            id="failed pipeline",
        ),
        pytest.param(
            "release",
            1,
            [],
            False,
            None,
            [],
            "timeout",
            id="timeout 1",
        ),
        pytest.param(
            "release",
            1,
            [],
            True,
            False,
            [],
            "timeout",
            id="timeout 2",
        ),
    ],
)
@patch("operatorcert.entrypoints.bulk_retrigger.wait_for_all_labels")
@patch("operatorcert.entrypoints.bulk_retrigger.wait_for_any_label")
def test_retrigger_pipeline_for_pr(
    mock_wait_any: MagicMock,
    mock_wait_all: MagicMock,
    pipeline: str,
    pr: int,
    initial_labels: list[str],
    wait_all_result: Optional[bool],
    wait_any_result: Optional[bool],
    final_labels: list[str],
    result: str,
) -> None:
    mock_wait_any.return_value = wait_any_result
    mock_wait_all.return_value = wait_all_result
    repo = MagicMock()
    pull = MagicMock()
    repo.get_pull = MagicMock()
    repo.get_pull.return_value = pull
    pull.get_labels = MagicMock()

    pull.get_labels.side_effect = [
        [mock_label(x) for x in initial_labels],
        [mock_label(x) for x in final_labels],
    ]
    assert retrigger_pipeline_for_pr(repo, pr, pipeline, 10) == result
    repo.get_pull.assert_called_once_with(pr)
    pull.get_labels.assert_called()
    if wait_all_result is not None:
        mock_wait_all.assert_called()
    else:
        mock_wait_all.assert_not_called()
    if wait_any_result is not None:
        mock_wait_any.assert_called()
    else:
        mock_wait_any.assert_not_called()


@pytest.mark.parametrize(
    [
        "present",
        "interval",
        "retries",
        "labels",
        "result",
    ],
    [
        pytest.param(
            {"foo"},
            5.0,
            10,
            [[], ["foo"]],
            True,
            id="single label; found",
        ),
        pytest.param(
            {"foo"},
            1.0,
            3,
            [["bar"], ["baz"], []],
            False,
            id="timeout",
        ),
        pytest.param(
            None,
            1.0,
            3,
            [],
            True,
            id="no label",
        ),
    ],
)
@patch("operatorcert.entrypoints.bulk_retrigger.time.sleep")
def test_wait_for_any_label(
    mock_sleep: MagicMock,
    present: Optional[set[str]],
    interval: float,
    retries: int,
    labels: list[list[str]],
    result: bool,
) -> None:
    pull = MagicMock()
    pull.get_labels = MagicMock()
    if labels:
        pull.get_labels.side_effect = [[mock_label(x) for x in y] for y in labels]
    assert wait_for_any_label(pull, present, interval, retries) == result
    mock_sleep.assert_has_calls([call(interval) for _ in labels])


@pytest.mark.parametrize(
    [
        "present",
        "absent",
        "interval",
        "retries",
        "labels",
        "result",
    ],
    [
        pytest.param(
            {"foo"},
            None,
            5.0,
            10,
            [[], ["foo"]],
            True,
            id="single label; found",
        ),
        pytest.param(
            {"foo"},
            None,
            1.0,
            3,
            [["bar"], ["bar", "baz"], ["baz"]],
            False,
            id="timeout",
        ),
        pytest.param(
            None,
            {"foo"},
            1.0,
            3,
            [["foo"], ["foo", "bar"], ["baz"]],
            True,
            id="absent",
        ),
    ],
)
@patch("operatorcert.entrypoints.bulk_retrigger.time.sleep")
def test_wait_for_all_labels(
    mock_sleep: MagicMock,
    present: Optional[set[str]],
    absent: Optional[set[str]],
    interval: float,
    retries: int,
    labels: list[list[str]],
    result: bool,
) -> None:
    pull = MagicMock()
    pull.get_labels = MagicMock()
    if labels:
        pull.get_labels.side_effect = [[mock_label(x) for x in y] for y in labels]
    assert wait_for_all_labels(pull, present, absent, interval, retries) == result
    mock_sleep.assert_has_calls([call(interval) for _ in labels])
