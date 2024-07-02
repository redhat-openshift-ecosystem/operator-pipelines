"""Create a fragment image dockerfile and build fragment image."""

import argparse
import json
import logging

from operatorcert import buildah, opm
from operatorcert.logger import setup_logger
from operatorcert.utils import SplitArgs

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        argparse.ArgumentParser: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Create a fragment image dockerfile and build fragment image."
    )
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to the repository with operators and catalogs",
    )
    parser.add_argument(
        "--catalog-names",
        default=[],
        action=SplitArgs,
        help="List of catalog names to build fragment images for",
    )
    parser.add_argument(
        "--repository-destination",
        required=True,
        help="Registry and repository where the fragment image will be pushed",
    )
    parser.add_argument("--tag-suffix", default="", help="Tag suffix for the image")
    parser.add_argument(
        "--authfile",
        default="~/.docker/config.json",
        help="A path to the authentication file",
    )
    parser.add_argument(
        "--output-file", help="Path to a json file where results will be stored"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def create_fragment_image(
    catalog_path: str, catalog_name: str, args: argparse.Namespace
) -> str:
    """
    Create a fragment image dockerfile, build fragment image and push it
    to a registry.

    Args:
        catalog_path (str): Path to a catalogs directory
        catalog_name (str): Name of the catalog in the catalogs directory
        args (argparse.Namespace): CLI arguments

    Returns:
        str: A pullspec of the pushed fragment image
    """
    dockerfile_path = opm.create_catalog_dockerfile(catalog_path, catalog_name)

    # Add '-<tag_suffix>' to the repository destination if tag_suffix is set
    suffix = f"-{args.tag_suffix}" if args.tag_suffix else ""
    repository_destination = f"{args.repository_destination}:{catalog_name}{suffix}"

    # Build and push the fragment image
    buildah.build_image(
        dockerfile_path,
        catalog_path,
        repository_destination,
    )
    buildah.push_image(repository_destination, args.authfile)

    return repository_destination


def main() -> None:
    """
    Main function of the script
    """
    # Args
    parser = setup_argparser()
    args = parser.parse_args()

    # Logging
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    output_images = {}

    # For each catalog, create a fragment image
    for catalog_name in args.catalog_names:
        catalog_path = f"{args.repo_path}/catalogs"
        fragment_image = create_fragment_image(catalog_path, catalog_name, args)
        output_images[catalog_name] = fragment_image

    LOGGER.info("Fragment images created: %s", output_images)

    # Save the results to a file
    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(output_images, f)


if __name__ == "__main__":  # pragma: no cover
    main()
