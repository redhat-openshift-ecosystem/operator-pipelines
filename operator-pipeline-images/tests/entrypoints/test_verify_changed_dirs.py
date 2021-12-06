from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import verify_changed_dirs


@patch("operatorcert.entrypoints.verify_changed_dirs.setup_argparser")
@patch("operatorcert.entrypoints.verify_changed_dirs.get_files_added_in_pr")
@patch("operatorcert.entrypoints.verify_changed_dirs.get_repo_and_org_from_github_url")
@patch("operatorcert.entrypoints.verify_changed_dirs.verify_changed_files_location")
def test_main(
    mock_verify_files: MagicMock,
    mock_get_url: MagicMock,
    mock_get_files: MagicMock,
    mock_arg_parser: MagicMock,
) -> None:
    mock_get_url.return_value = "redhat-openshift-ecosystem", "operator-pipelines"
    verify_changed_dirs.main()
    mock_get_files.assert_called_once()
    mock_verify_files.assert_called_once()
