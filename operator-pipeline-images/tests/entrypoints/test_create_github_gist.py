from typing import Any
from unittest import mock
from unittest.mock import MagicMock, patch, call

from operatorcert.entrypoints.create_github_gist import (
    create_github_gist,
    main,
    setup_argparser,
    share_github_gist,
)


@patch("operatorcert.entrypoints.create_github_gist.json.dump")
@patch("operatorcert.entrypoints.create_github_gist.share_github_gist")
@patch("operatorcert.entrypoints.create_github_gist.create_github_gist")
@patch("operatorcert.entrypoints.create_github_gist.Github")
@patch("operatorcert.entrypoints.create_github_gist.setup_logger")
@patch("operatorcert.entrypoints.create_github_gist.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_github: MagicMock,
    mock_create_github_gist: MagicMock,
    mock_share_github_gist: MagicMock,
    mock_json_dump: MagicMock,
    monkeypatch: Any,
) -> None:
    args = MagicMock()
    args.input_file = ["some_file"]
    args.output_file = "tmp/output.json"
    args.pull_request_url = "https://github.com/foo/bar/pull/123"
    args.comment_prefix = "prefix:"
    mock_setup_argparser.return_value.parse_args.return_value = args

    mock_open = mock.mock_open(read_data="foo")

    monkeypatch.setenv("GITHUB_TOKEN", "foo_api_token")
    with mock.patch("builtins.open", mock_open):
        main()

    mock_create_github_gist.assert_called_once_with(mock_github(), ["some_file"])
    mock_share_github_gist.assert_called_once_with(
        mock_github(), "foo/bar", 123, mock_create_github_gist.return_value, "prefix:"
    )
    mock_json_dump.assert_called_once_with(
        {"gist_url": mock_create_github_gist.return_value.html_url}, mock.ANY
    )


@patch("operatorcert.entrypoints.create_github_gist.InputFileContent")
def test_create_github_gist(mock_input_file_content: MagicMock) -> None:
    mock_open = mock.mock_open(read_data="foo")
    mock_github = MagicMock()

    github_user = MagicMock()
    mock_github.get_user.return_value = github_user
    github_user.create_gist.return_value = MagicMock(html_url="some_url")
    with mock.patch("builtins.open", mock_open):
        resp = create_github_gist(mock_github, ["some_file", "file2"])

    mock_input_file_content.assert_has_calls([call("foo"), call("foo")])
    github_user.create_gist.assert_called_once_with(
        True,
        {
            "some_file": mock_input_file_content.return_value,
            "file2": mock_input_file_content.return_value,
        },
    )
    assert resp == github_user.create_gist.return_value


def test_share_github_gist() -> None:
    mock_github = MagicMock()
    mock_pull_request = MagicMock()
    mock_github.get_repo.return_value.get_pull.return_value = mock_pull_request
    share_github_gist(
        mock_github, "foo/bar", 123, MagicMock(html_url="some_url"), "Logs: "
    )

    mock_github.get_repo.assert_called_once_with("foo/bar")
    mock_github.get_repo.return_value.get_pull.assert_called_once_with(123)
    mock_pull_request.create_issue_comment.assert_called_once_with("Logs: some_url")


def test_setup_argparser() -> None:
    assert setup_argparser() is not None
