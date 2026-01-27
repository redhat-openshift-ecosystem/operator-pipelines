from unittest.mock import MagicMock, patch
from typing import Any
import textwrap

from operatorcert.entrypoints import github_pr


@patch("operatorcert.entrypoints.github_pr.github.post")
def test_open_pr(mock_post: MagicMock, monkeypatch: Any) -> None:
    mock_post.return_value = {}
    resp = github_pr.open_pr(
        "http://foo.com/v1", "repo/name", "branch1", "main", "title", "Body"
    )

    mock_post.assert_called_once()

    assert resp == {}


def test_get_head() -> None:
    resp = github_pr.get_head("git@github.com:user/repo.git", "main")
    assert resp == "user:main"

    resp = github_pr.get_head("https://github.com/org/repo.git", "foo")
    assert resp == "org:foo"


def test_get_pr_body() -> None:
    args = MagicMock()
    args.title = "operator foo (1.0.0)"
    args.cert_project_id = "0123"
    args.test_result_url = "https://foo.com/tests"
    args.test_logs_url = "https://foo.com/logs"

    resp = github_pr.get_pr_body(args)

    expected = """\
    **New operator bundle**

    Name: **foo**
    Version: **1.0.0**

    Certification project: 0123

    Test result URL: https://foo.com/tests
    Test logs URL: https://foo.com/logs
    """

    assert resp == textwrap.dedent(expected)
