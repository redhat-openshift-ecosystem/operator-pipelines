from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import verify_pr_title


@patch("operatorcert.entrypoints.verify_pr_title.setup_argparser")
@patch("operatorcert.entrypoints.verify_pr_title.parse_pr_title")
@patch("operatorcert.entrypoints.verify_pr_title.store_results")
def test_main(
    mock_results: MagicMock, mock_title: MagicMock, mock_arg_parser: MagicMock
) -> None:
    mock_title.return_value = "demo", "response"
    verify_pr_title.main()
    mock_results.assert_called_once()
