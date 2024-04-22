import pytest

from unittest.mock import MagicMock, patch, call
from subprocess import CalledProcessError

import operatorcert.entrypoints.validate_catalog_format as validate_catalog_format


@patch("operatorcert.entrypoints.validate_catalog_format.run_command")
def test_run_makefile(mock_run_command: MagicMock) -> None:

    validate_catalog_format.run_makefile("path/to/operator/Makefile")

    mock_run_command.assert_called_once_with(
        ["make", "catalog", "-f", "path/to/operator/Makefile"]
    )


@patch("operatorcert.entrypoints.validate_catalog_format.run_command")
def test_check_altered(mock_run_command: MagicMock) -> None:

    validate_catalog_format.check_altered()

    mock_run_command.assert_called_once_with(["git", "diff", "--quiet"])


@patch("operatorcert.entrypoints.validate_catalog_format.run_command")
def test_validate_catalog_format(mock_run_command: MagicMock) -> None:

    validate_catalog_format.validate_catalog_format("path/to/catalogs", "catalog1")

    mock_run_command.assert_called_once_with(
        ["opm", "validate", "path/to/catalogs/catalog1"]
    )


@patch("operatorcert.entrypoints.validate_catalog_format.check_altered")
@patch("operatorcert.entrypoints.validate_catalog_format.run_makefile")
@patch("operatorcert.entrypoints.validate_catalog_format.validate_catalog_format")
@patch("operatorcert.entrypoints.validate_catalog_format.setup_logger")
@patch("operatorcert.entrypoints.validate_catalog_format.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_validate_catalog_format: MagicMock,
    mock_run_makefile: MagicMock,
    mock_check_altered: MagicMock,
) -> None:
    args = MagicMock()
    args.catalog_names = ["catalog1", "catalog2"]
    args.repo_path = "repo"
    args.makefile_path = "path/to/repo/Makefile"

    mock_setup_argparser.return_value.parse_args.return_value = args

    validate_catalog_format.main()

    catalogs_path = args.repo_path + "/catalogs"

    mock_validate_catalog_format.assert_has_calls(
        [call(catalogs_path, "catalog1"), call(catalogs_path, "catalog2")]
    )

    mock_run_makefile.assert_called_once_with(args.makefile_path)
    mock_check_altered.assert_called_once()


@patch("operatorcert.entrypoints.validate_catalog_format.validate_catalog_format")
@patch("operatorcert.entrypoints.validate_catalog_format.setup_logger")
@patch("operatorcert.entrypoints.validate_catalog_format.setup_argparser")
def test_main_invalid_catalog(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_validate_catalog_format: MagicMock,
) -> None:
    args = MagicMock()
    args.catalog_names = ["catalog1"]
    mock_setup_argparser.return_value.parse_args.return_value = args

    mock_validate_catalog_format.side_effect = CalledProcessError(1, "opm validate")

    with pytest.raises(SystemExit) as invalid_catalog:
        validate_catalog_format.main()
        assert invalid_catalog.type == SystemExit


@patch("operatorcert.entrypoints.validate_catalog_format.check_altered")
@patch("operatorcert.entrypoints.validate_catalog_format.run_makefile")
@patch("operatorcert.entrypoints.validate_catalog_format.validate_catalog_format")
@patch("operatorcert.entrypoints.validate_catalog_format.setup_logger")
@patch("operatorcert.entrypoints.validate_catalog_format.setup_argparser")
def test_main_changed_by_makefile(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_validate_catalog_format: MagicMock,
    mock_run_makefile: MagicMock,
    mock_check_altered: MagicMock,
) -> None:
    args = MagicMock()
    args.catalog_names = ["catalog1"]
    args.repo_path = "repo"
    args.makefile_path = "path/to/repo/Makefile"
    mock_setup_argparser.return_value.parse_args.return_value = args

    mock_check_altered.side_effect = CalledProcessError(1, "git diff --quiet")

    with pytest.raises(CalledProcessError):
        validate_catalog_format.main()

        mock_validate_catalog_format.assert_called_once_with(
            args.repo_path + "/catalogs", "catalog1"
        )
        mock_run_makefile.assert_called_once_with(args.makefile_path)
        mock_check_altered.assert_called_once()


def test_setup_argparser() -> None:
    assert validate_catalog_format.setup_argparser() is not None
