from operatorcert.community_prow.main import main
from unittest.mock import patch, MagicMock


# placeholder test for initial entrypoint
@patch("operatorcert.community_prow.main.setup_logger")
def test_main(mock_setup_logger: MagicMock) -> None:
    mock_setup_logger.return_value = "test prow"
    main()
