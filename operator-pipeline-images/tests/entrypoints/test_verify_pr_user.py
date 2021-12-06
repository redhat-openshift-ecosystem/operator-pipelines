from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import verify_pr_user


@patch("operatorcert.entrypoints.verify_pr_user.setup_argparser")
@patch("operatorcert.entrypoints.verify_pr_user.validate_user")
def test_main(mock_user: MagicMock, mock_arg_parser: MagicMock) -> None:
    verify_pr_user.main()
    mock_user.assert_called_once()
