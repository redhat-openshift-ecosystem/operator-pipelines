import pathlib
from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import github_add_comment

GITHUB_HOST_URL = "https://api.github.com"
PARENT_DIR = pathlib.Path(__file__).parent.resolve()
COMMENT_PATH = PARENT_DIR.joinpath("../data/comment.txt")
REQUEST_URL = "https://github.com/redhat-openshift-ecosystem/operator-pipelines/pull/252"


@patch("operatorcert.entrypoints.github_add_comment.github.post")
def test_github_add_comment_POST(mock_post: MagicMock) -> None:
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
        args.replace
    )
    mock_post.assert_called_once_with(
        "https://api.github.com/repos/redhat-openshift-ecosystem/operator-pipelines/issues/252/comments",
        {
            "body": "Test comment.<!-- test_tag -->"
        },
    )

@patch("operatorcert.entrypoints.github_add_comment.github.get")
@patch("operatorcert.entrypoints.github_add_comment.github.patch")
def test_github_add_comment_PATCH(mock_get: MagicMock, mock_patch: MagicMock) -> None:
    args = MagicMock()
    args.github_host_url = GITHUB_HOST_URL
    args.request_url = REQUEST_URL
    args.comment_file = COMMENT_PATH
    args.comment_tag = "test_tag_2"
    args.replace = "true"

    mock_get.return_value = [
        {
            "body": "Test comment.<!-- test_tag_2 -->",
            "url": "https://api.github.com/repos/redhat-openshift-ecosystem/operator-pipelines/test/comment/123456"
        }
    ]
    github_add_comment.github_add_comment(
        args.github_host_url,
        args.request_url,
        args.comment_file,
        args.comment_tag,
        args.replace
    )
    mock_get.assert_called_once_with(
        "https://api.github.com/repos/redhat-openshift-ecosystem/operator-pipelines/test/comment/123456",
    )
    mock_patch.assert_called_once_with(
        "https://api.github.com/repos/redhat-openshift-ecosystem/operator-pipelines/test/comment/123456",
        {
            "body": "Test comment.<!-- test_tag_2 -->"
        },
    )
