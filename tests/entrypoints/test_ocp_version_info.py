from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import ocp_version_info


@patch("operatorcert.entrypoints.ocp_version_info.setup_argparser")
@patch("operatorcert.entrypoints.ocp_version_info.pathlib.Path")
@patch("operatorcert.entrypoints.ocp_version_info.Repo")
@patch("operatorcert.entrypoints.ocp_version_info.ocp_version_info")
def test_main(
    mock_version_info: MagicMock,
    mock_repo: MagicMock,
    mock_path: MagicMock,
    mock_arg_parser: MagicMock,
) -> None:
    mock_version_info.return_value = {
        "indices": "indices",
        "max_version_index": "sample_index",
    }
    ocp_version_info.main()
    mock_version_info.assert_called_once()
