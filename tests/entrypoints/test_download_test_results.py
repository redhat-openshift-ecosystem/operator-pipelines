from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import download_test_results


@patch("operatorcert.entrypoints.download_test_results.setup_argparser")
@patch("operatorcert.entrypoints.download_test_results.download_test_results")
@patch("operatorcert.entrypoints.download_test_results.store_results")
def test_main(
    mock_results: MagicMock, mock_download: MagicMock, mock_arg_parser: MagicMock
) -> None:
    download_test_results.main()
    mock_download.assert_called_once()
    mock_results.assert_called_once()
