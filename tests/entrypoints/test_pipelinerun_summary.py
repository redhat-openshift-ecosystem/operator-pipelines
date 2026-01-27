from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import pipelinerun_summary


@patch("operatorcert.entrypoints.pipelinerun_summary.argparse")
@patch("operatorcert.entrypoints.pipelinerun_summary.PipelineRun.from_files")
def test_main(mock_files: MagicMock, mock_arg_parser: MagicMock) -> None:
    pipelinerun_summary.main()
    mock_files.assert_called_once()
