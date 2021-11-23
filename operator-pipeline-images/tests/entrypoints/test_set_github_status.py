from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import set_github_status


@patch("operatorcert.entrypoints.set_github_status.setup_argparser")
@patch("operatorcert.entrypoints.set_github_status.set_github_status")
def test_main(
    mock_github_status: MagicMock,
    mock_arg_parser: MagicMock,
) -> None:
    set_github_status.main()
    mock_github_status.assert_called_once()


@patch("operatorcert.entrypoints.set_github_status.github.post")
@patch("operatorcert.entrypoints.set_github_status.get_repo_and_org_from_github_url")
def test_set_github_status(
    mock_url: MagicMock,
    mock_post: MagicMock,
):
    args = MagicMock()
    args.commit_sha = "b991e252da91df5429e9b2b26d6f88d681a8f754"
    args.context = "operator/test"
    args.descripton = "demo"
    args.state = "pending"
    args.target_url = "https://api.github.com"
    mock_url.return_value = "redhat-openshift-ecosystem", "operator-pipelines"

    set_github_status.set_github_status(args)
    mock_post.assert_called_once_with(
        "https://api.github.com/repos/redhat-openshift-ecosystem/operator-pipelines/statuses/b991e252da91df5429e9b2b26d6f88d681a8f754",
        {
            "context": args.context,
            "description": args.description,
            "state": args.status,
            "target_url": args.target_url,
        },
    )
