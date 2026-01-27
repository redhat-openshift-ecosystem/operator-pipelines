import logging
from argparse import Namespace
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

from operatorcert.entrypoints.integration_tests import (
    main,
    parse_args,
    setup_logging,
)


def test_parse_args() -> None:
    args = [
        "integration-tests",
        "-v",
        "-i",
        "quay.io/foo/bar:latest",
        "/foo",
        "/bar/config.yaml",
    ]
    with patch("sys.argv", args):
        result = parse_args()
        assert result.verbose == True
        assert result.image == "quay.io/foo/bar:latest"
        assert result.directory == Path("/foo")
        assert result.config_file == Path("/bar/config.yaml")


@patch("operatorcert.entrypoints.integration_tests.logging.basicConfig")
def test_setup_logging(mock_basicconfig: MagicMock) -> None:
    setup_logging(True)
    mock_basicconfig.assert_called_once_with(format=ANY, level=logging.DEBUG)


@patch("operatorcert.entrypoints.integration_tests.parse_args")
@patch("operatorcert.entrypoints.integration_tests.setup_logging")
@patch("operatorcert.entrypoints.integration_tests.run_integration_tests")
def test_main(
    mock_run_integration_tests: MagicMock,
    mock_setup_logging: MagicMock,
    mock_parse_args: MagicMock,
) -> None:
    mock_parse_args.return_value = Namespace(
        verbose=True,
        image="quay.io/foo/bar:latest",
        directory=Path("/foo"),
        config_file=Path("/bar/config.yaml"),
    )
    main()
    mock_parse_args.assert_called_once()
    mock_setup_logging.assert_called_once_with(True)
    mock_run_integration_tests.assert_called_once_with(
        Path("/foo"), Path("/bar/config.yaml"), "quay.io/foo/bar:latest"
    )
