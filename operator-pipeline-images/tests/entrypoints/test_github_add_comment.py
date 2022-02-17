from logging import raiseExceptions
import pathlib
from unittest.mock import MagicMock, patch
from requests import HTTPError

from operatorcert.entrypoints import github_add_comment
import pytest

GITHUB_HOST_URL = "https://api.github.com"
PARENT_DIR = pathlib.Path(__file__).parent.resolve()
COMMENT_PATH = PARENT_DIR.joinpath("../data/comment.txt")
REQUEST_URL = (
    "https://github.com/redhat-openshift-ecosystem/operator-pipelines/pull/252"
)


@patch("operatorcert.entrypoints.github_add_comment.github.post")
def test_github_add_comment_post(mock_post: MagicMock) -> None:
    args = MagicMock()
    args.github_host_url = GITHUB_HOST_URL
    args.request_url = REQUEST_URL
    args.comment_file = COMMENT_PATH
    args.comment_tag = "test_tag"

    github_add_comment.github_add_comment(
        args.github_host_url,
        args.request_url,
        args.comment_file,
        args.comment_tag,
        args.replace,
    )
    mock_post.assert_called_once_with(
        "https://api.github.com/repos/redhat-openshift-ecosystem/operator-pipelines/issues/252/comments",
        {"body": "Test comment.<!-- test_tag -->"},
    )


@patch("operatorcert.entrypoints.github_add_comment.github.get")
@patch("operatorcert.entrypoints.github_add_comment.github.patch")
def test_github_add_comment_patch(mock_patch: MagicMock, mock_get: MagicMock) -> None:
    args = MagicMock()
    args.github_host_url = GITHUB_HOST_URL
    args.request_url = REQUEST_URL
    args.comment_file = COMMENT_PATH
    args.comment_tag = "test_tag_2"
    args.replace = "true"

    mock_get.return_value = [
        {
            "body": "Test comment.<!-- test_tag_2 -->",
            "url": "https://api.github.com/repos/redhat-openshift-ecosystem/operator-pipelines/test/comment/123456",
        }
    ]
    github_add_comment.github_add_comment(
        args.github_host_url,
        args.request_url,
        args.comment_file,
        args.comment_tag,
        args.replace,
    )
    mock_get.assert_called_once_with(
        "https://api.github.com/repos/redhat-openshift-ecosystem/operator-pipelines/issues/252/comments",
    )
    mock_patch.assert_called_once_with(
        "https://api.github.com/repos/redhat-openshift-ecosystem/operator-pipelines/test/comment/123456",
        {"body": "Test comment.<!-- test_tag_2 -->"},
    )


def test_github_add_comment_no_tag_replace_true() -> None:
    args = MagicMock()
    args.github_host_url = GITHUB_HOST_URL
    args.request_url = REQUEST_URL
    args.comment_file = COMMENT_PATH
    args.comment_tag = ""
    args.replace = "true"

    with pytest.raises(SystemExit) as notag_exit:
        github_add_comment.github_add_comment(
            args.github_host_url,
            args.request_url,
            args.comment_file,
            args.comment_tag,
            args.replace,
        )
    assert notag_exit.type == SystemExit


@patch("operatorcert.entrypoints.github_add_comment.github.post")
def test_github_add_comment_bad_address_post(mock_post: MagicMock) -> None:
    args = MagicMock()
    args.github_host_url = GITHUB_HOST_URL
    args.request_url = "https://github.com/foo/bar/pull/202"
    args.comment_file = COMMENT_PATH

    mock_post.side_effect = HTTPError

    with pytest.raises(SystemExit) as bad_address:
        github_add_comment.github_add_comment(
            args.github_host_url,
            args.request_url,
            args.comment_file,
            args.comment_tag,
            args.replace,
        )
    assert bad_address.type == SystemExit


@patch("operatorcert.entrypoints.github_add_comment.github.patch")
@patch("operatorcert.entrypoints.github_add_comment.github.get")
def test_github_add_comment_bad_address_patch(
    mock_get: MagicMock, mock_patch: MagicMock
) -> None:
    args = MagicMock()
    args.github_host_url = GITHUB_HOST_URL
    args.request_url = "https://github.com/foo/bar/pull/202"
    args.comment_file = COMMENT_PATH
    args.comment_tag = "test_tag_3"
    args.replace = "true"

    mock_get.return_value = [
        {
            "body": "Test comment.<!-- test_tag_3 -->",
            "url": "https://api.github.com/repos/redhat-openshift-ecosystem/operator-pipelines/test/comment/123456",
        }
    ]

    mock_patch.side_effect = HTTPError

    with pytest.raises(SystemExit) as bad_address:
        github_add_comment.github_add_comment(
            args.github_host_url,
            args.request_url,
            args.comment_file,
            args.comment_tag,
            args.replace,
        )
    assert bad_address.type == SystemExit


@patch("operatorcert.entrypoints.github_add_comment.github.get")
def test_github_add_comment_bad_address_replace(mock_get: MagicMock) -> None:
    args = MagicMock()
    args.github_host_url = GITHUB_HOST_URL
    args.request_url = "https://github.com/foo/bar/pull/202"
    args.comment_file = COMMENT_PATH
    args.comment_tag = "test_tag_4"
    args.replace = "true"

    mock_get.side_effect = HTTPError

    with pytest.raises(SystemExit) as bad_address:
        github_add_comment.github_add_comment(
            args.github_host_url,
            args.request_url,
            args.comment_file,
            args.comment_tag,
            args.replace,
        )
    assert bad_address.type == SystemExit
