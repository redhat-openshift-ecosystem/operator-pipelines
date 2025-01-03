from unittest.mock import MagicMock, patch

from operatorcert.catalog import catalog_cli


def test_setup_argparser() -> None:
    parser = catalog_cli.setup_argparser()
    assert parser


@patch("operatorcert.catalog.catalog_cli.Catalog.from_file")
@patch("operatorcert.catalog.catalog_cli.CatalogImage")
@patch("operatorcert.catalog.catalog_cli.handle_list_command")
@patch("operatorcert.catalog.catalog_cli.handle_show_command")
@patch("operatorcert.catalog.catalog_cli.setup_argparser")
def test_main(
    mock_argparser: MagicMock,
    mock_handle_show_command: MagicMock,
    mock_handle_list_command: MagicMock,
    mock_catalog_image: MagicMock,
    mock_catalog_from_file: MagicMock,
) -> None:
    mock_argparser.return_value.parse_args.return_value = MagicMock(
        command="list", content_type="packages", image="fake.img"
    )

    catalog_cli.main()

    mock_handle_list_command.assert_called_once()
    mock_handle_show_command.assert_not_called()

    mock_handle_list_command.reset_mock()
    mock_handle_show_command.reset_mock()
    mock_argparser.return_value.parse_args.return_value = MagicMock(
        command="show",
        content_type="package",
        rendered=True,
        image=None,
    )

    catalog_cli.main()

    mock_handle_list_command.assert_not_called()
    mock_handle_show_command.assert_called_once()


def test_handle_show_command() -> None:
    args = MagicMock(content_type="package")
    catalog = MagicMock()
    catalog_cli.handle_show_command(args, catalog)

    catalog.get_package.assert_called_once()

    args = MagicMock(content_type="channel")
    catalog = MagicMock()
    catalog.get_channels.return_value = [MagicMock()]
    catalog_cli.handle_show_command(args, catalog)

    catalog.get_channels.assert_called_once()

    args = MagicMock(content_type="bundle")
    catalog = MagicMock()
    catalog_cli.handle_show_command(args, catalog)

    catalog.get_bundle.assert_called_once()


def test_handle_list_command() -> None:
    args = MagicMock(content_type="packages", package="foo")
    catalog = MagicMock()
    pkg = MagicMock()
    pkg.name = "foo"
    catalog.get_all_packages.return_value = [pkg]
    catalog_cli.handle_list_command(args, catalog)

    catalog.get_all_packages.assert_called_once()

    args = MagicMock(content_type="channels", channel="foo")
    catalog = MagicMock()
    channel = MagicMock()
    channel.name = "foo"
    catalog.get_all_channels.return_value = [channel]
    catalog_cli.handle_list_command(args, catalog)

    catalog.get_all_channels.assert_called_once()

    args = MagicMock(content_type="bundles", bundle=None)
    catalog = MagicMock()
    catalog.get_all_bundles.return_value = [MagicMock()]
    catalog_cli.handle_list_command(args, catalog)

    catalog.get_all_bundles.assert_called_once()

    args = MagicMock(content_type="bundles", bundle="foo")
    catalog = MagicMock()
    catalog.get_bundle.return_value = MagicMock()
    catalog_cli.handle_list_command(args, catalog)

    catalog.get_bundle.assert_called_once()
