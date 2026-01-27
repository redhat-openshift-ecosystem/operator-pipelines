"""A cli tool for browsing and querying index image content."""

import argparse
from typing import Any

from operatorcert.catalog.catalog import Catalog, CatalogImage


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Browse and query index image content."
    )

    # Global options
    parser.add_argument("--image", type=str, help="Path to the index image.")
    parser.add_argument(
        "--rendered", type=str, help="Path to the rendered index image content."
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Commands")

    # 'list' command
    list_parser = subparsers.add_parser(
        "list",
        help="List content in the index image.",
    )
    list_parser.add_argument(
        "content_type",
        type=str,
        choices=["packages", "channels", "bundles"],
        help="Type of content to list.",
    )
    list_parser.add_argument("--package", type=str, help="Filter by package name.")
    list_parser.add_argument("--channel", type=str, help="Filter by channel name.")
    list_parser.add_argument("--bundle", type=str, help="Filter by bundle name.")

    # 'show' command
    show_parser = subparsers.add_parser(
        "show", help="Show details of specific content."
    )
    show_parser.add_argument(
        "content_type",
        type=str,
        choices=["package", "channel", "bundle"],
        help="Type of content to show.",
    )
    show_parser.add_argument("name", type=str, help="Name of the content to show.")

    return parser


def handle_list_command(args: Any, catalog: Catalog) -> None:
    """
    List content in the index image based on the provided arguments.

    The function prints the content to the console.

    Args:
        args (Any): Arguments provided by the user.
        catalog (Catalog): A Catalog object representing the index image.
    """
    if args.content_type == "packages":
        packages = catalog.get_all_packages()
        if args.package:
            packages = [p for p in packages if p.name == args.package]
        for package in packages:
            print(package)
    elif args.content_type == "channels":
        channels = catalog.get_all_channels()
        if args.channel:
            channels = [c for c in channels if c.name == args.channel]
        for channel in channels:
            print(channel)
    elif args.content_type == "bundles":
        if args.bundle:
            bundles = []
            bundle = catalog.get_bundle(args.bundle)
            if bundle:
                bundles.append(bundle)
        else:
            bundles = catalog.get_all_bundles()
        for bundle in bundles:
            print(bundle)


def handle_show_command(args: Any, catalog: Catalog) -> None:
    """
    Show details of specific content based on the provided arguments.

    A function prints the content to the console in a human-readable format.

    Args:
        args (Any): Arguments provided by the user.
        catalog (Catalog): A Catalog object representing the index image.
    """
    if args.content_type == "package":
        package = catalog.get_package(args.name)
        if package:
            package.print()
    elif args.content_type == "channel":
        channels = catalog.get_channels(args.name)
        for channel in channels:
            channel.print()
    elif args.content_type == "bundle":
        bundle = catalog.get_bundle(args.name)
        if bundle:
            bundle.print()


def main() -> None:
    """
    Main function for the cli tool.
    """
    parser = setup_argparser()
    args = parser.parse_args()
    catalog = None
    if args.image:
        catalog_image = CatalogImage(args.image)
        catalog = catalog_image.catalog_content
    elif args.rendered:
        catalog = Catalog.from_file(args.rendered)

    if catalog:
        if args.command == "list":
            handle_list_command(args, catalog)
        elif args.command == "show":
            handle_show_command(args, catalog)


if __name__ == "__main__":  # pragma: no cover
    main()
