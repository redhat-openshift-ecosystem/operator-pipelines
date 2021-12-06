from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import verify_pr_uniqueness


@patch("operatorcert.entrypoints.verify_pr_uniqueness.setup_argparser")
@patch("operatorcert.entrypoints.verify_pr_uniqueness.verify_pr_uniqueness")
def test_main(mock_uniqueness: MagicMock, mock_arg_parser: MagicMock) -> None:
    verify_pr_uniqueness.main()
    mock_uniqueness.assert_called_once()
