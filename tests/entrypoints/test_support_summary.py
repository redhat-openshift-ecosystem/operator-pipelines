from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import quote_plus

from operatorcert.entrypoints import support_summary


def test_CategorySummary() -> None:
    summary = support_summary.CategorySummary(
        "name",
        [],
        "summary",
    )
    assert str(summary) == "📌 *Name*\nsummary"

    summary = support_summary.CategorySummary(
        "name",
        ["item1", "item2"],
        "summary",
        "instructions",
    )
    assert str(summary) == "📌 *Name*\nsummary\n*Instructions:* instructions"


@patch("operatorcert.entrypoints.support_summary.Github")
@patch("operatorcert.entrypoints.support_summary.generate_summary_comment")
def test_main(
    mock_generate_summary_comment: MagicMock, mock_github: MagicMock, monkeypatch: Any
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "123")
    support_summary.main()
    mock_github.assert_called_once()
    mock_generate_summary_comment.assert_called_once()


@patch("operatorcert.entrypoints.support_summary.requests")
@patch("operatorcert.entrypoints.support_summary.Misc")
@patch("operatorcert.entrypoints.support_summary.NewIssues")
@patch("operatorcert.entrypoints.support_summary.K8sPullRequestReview")
@patch("operatorcert.entrypoints.support_summary.OCPFailedHostedPipeline")
@patch("operatorcert.entrypoints.support_summary.OCPFailedReleasePipeline")
@patch("operatorcert.entrypoints.support_summary.OCPPullRequestReview")
def test_generate_summary_comment(
    mock_ocp_pull: MagicMock,
    mock_release: MagicMock,
    mock_hosted: MagicMock,
    mock_k8s: MagicMock,
    mock_issues: MagicMock,
    mock_misc: MagicMock,
    mock_requests: MagicMock,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "123")
    gh_client = MagicMock()
    support_summary.generate_summary_comment(gh_client)

    mock_ocp_pull.return_value.run.assert_called_once()
    mock_release.return_value.run.assert_called_once()
    mock_hosted.return_value.run.assert_called_once()
    mock_k8s.return_value.run.assert_called_once()
    mock_issues.return_value.run.assert_called_once()
    mock_misc.return_value.run.assert_called_once()

    mock_requests.post.assert_called_once()


@patch("operatorcert.entrypoints.support_summary.CategoryChecker.to_summary_text")
def test_OCPPullRequestReview(mock_to_summary: MagicMock) -> None:
    gh_client = MagicMock()
    checker = support_summary.OCPPullRequestReview(gh_client, ["repo"])
    assert (
        "repo:repo is:pr is:open label:operator-hosted-pipeline/passed" in checker.query
    )

    result = checker.run()
    mock_to_summary.assert_called_once()
    assert isinstance(result, support_summary.CategorySummary)
    gh_client.search_issues.assert_called_once()


@patch("operatorcert.entrypoints.support_summary.CategoryChecker.to_summary_text")
def test_OCPFailedReleasePipeline(mock_to_summary: MagicMock) -> None:
    gh_client = MagicMock()
    checker = support_summary.OCPFailedReleasePipeline(gh_client, ["repo"])
    assert (
        "repo:repo is:pr label:operator-release-pipeline/failed is:closed"
        in checker.query
    )

    result = checker.run()
    mock_to_summary.assert_called_once()
    assert isinstance(result, support_summary.CategorySummary)
    gh_client.search_issues.assert_called_once()


@patch("operatorcert.entrypoints.support_summary.CategoryChecker.to_summary_text")
def test_OCPFailedHostedPipeline(mock_to_summary: MagicMock) -> None:
    gh_client = MagicMock()
    checker = support_summary.OCPFailedHostedPipeline(gh_client, ["repo"])
    assert (
        "repo:repo is:pr is:open label:operator-hosted-pipeline/failed" in checker.query
    )

    result = checker.run()
    mock_to_summary.assert_called_once()
    assert isinstance(result, support_summary.CategorySummary)
    gh_client.search_issues.assert_called_once()


@patch("operatorcert.entrypoints.support_summary.CategoryChecker.to_summary_text")
def test_K8sPullRequestReview(mock_to_summary: MagicMock) -> None:
    gh_client = MagicMock()
    checker = support_summary.K8sPullRequestReview(gh_client, ["repo"])
    assert (
        "repo:repo is:pr -label:authorized-changes is:open status:success"
        in checker.query
    )

    result = checker.run()
    mock_to_summary.assert_called_once()
    assert isinstance(result, support_summary.CategorySummary)
    gh_client.search_issues.assert_called_once()


@patch("operatorcert.entrypoints.support_summary.CategoryChecker.to_summary_text")
def test_NewIssues(mock_to_summary: MagicMock) -> None:
    gh_client = MagicMock()
    checker = support_summary.NewIssues(gh_client, ["repo"])
    assert "repo:repo is:issue created:>=" in checker.query

    result = checker.run()
    mock_to_summary.assert_called_once()
    assert isinstance(result, support_summary.CategorySummary)
    gh_client.search_issues.assert_called_once()

    assert checker.github_link == "https://github.com/search?q=" + quote_plus(
        checker.query
    )


def test_Misc() -> None:
    gh_client = MagicMock()
    checker = support_summary.Misc(gh_client)

    result = checker.run()
    assert isinstance(result, support_summary.CategorySummary)

    assert result.summary_text.startswith("Keep an eye on Slack channels")
