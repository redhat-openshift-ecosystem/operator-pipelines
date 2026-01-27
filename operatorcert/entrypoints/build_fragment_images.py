"""Create a fragment image dockerfile and build fragment image."""

import argparse
import json
import logging
import shutil
import tempfile
from pathlib import Path

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
        default=Path("."),
        help="Path to the repository with operators and catalogs",
        type=Path,
    )
    parser.add_argument(
        "--catalog-operators",
        default=[],
        action=SplitArgs,
        help="List of catalog operators to include in the"
        "fragment image separated by comma. Catalog operator should be in format "
        "<catalog_name>/<operator_name>",
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


def select_operator_for_catalog(
    catalog_path: Path, catalog_name: str, operators: list[str], dest_path: Path
) -> Path:
    """
    Select a subset of operators from a catalog and move them into new
    location given by the destination parameter.

    Args:
        catalog_path (Path): A path to a catalogs directory
        catalog_name (str): A name of the catalog in the catalogs directory
        operators (list[str]): A list of operators to select from the catalog
        dest_path (Path): A path to the destination directory

    Returns:
        Path: Path to the selected catalog in the destination directory
    """

    for operator in operators:
        src_path = catalog_path / catalog_name / operator
        dest_operator_path = dest_path / catalog_name / operator
        shutil.copytree(src_path, dest_operator_path)

    return dest_path / catalog_name


def create_fragment_image(
    catalog_path: Path,
    catalog_name: str,
    operators: list[str],
    args: argparse.Namespace,
) -> str:
    """
    Create a fragment image dockerfile, build fragment image and push it
    to a registry.

    Args:
        catalog_path (Path): Path to a catalogs directory
        catalog_name (str): Name of the catalog in the catalogs directory
        args (argparse.Namespace): CLI arguments

    Returns:
        str: A pullspec of the pushed fragment image
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        LOGGER.debug("Creating fragment image for catalog: %s", catalog_name)
        LOGGER.debug("Operators to include: %s", operators)

        select_operator_for_catalog(catalog_path, catalog_name, operators, Path(tmpdir))

        dockerfile_path = opm.create_catalog_dockerfile(Path(tmpdir), catalog_name)

        # Add '-<tag_suffix>' to the repository destination if tag_suffix is set
        suffix = f"-{args.tag_suffix}" if args.tag_suffix else ""
        repository_destination = f"{args.repository_destination}:{catalog_name}{suffix}"

        # Build and push the fragment image
        buildah.build_image(
            dockerfile_path.as_posix(),
            tmpdir,
            repository_destination,
        )
        buildah.push_image(repository_destination, args.authfile)

        return repository_destination


def group_operators_by_catalog(catalog_operators: list[str]) -> dict[str, list[str]]:
    """
    Create a groups of catalog and operators in the dict format. Catalogs
    are represented as a dict keys and operators are stored as value list

    Args:
        catalog_operators (list[str]): A list of catalog operators in a format of
        "<catalog_name>/<operator_name>"

    Returns:
        dict[str, list[str]]: A dictionary where key is catalog name and value is
        a list of operators within the catalog
    """

    catalog_to_operator_mapping: dict[str, list[str]] = {}
    for catalog_operator in catalog_operators:
        catalog, operator = catalog_operator.split("/", 1)
        if catalog not in catalog_to_operator_mapping:
            catalog_to_operator_mapping[catalog] = []
        catalog_to_operator_mapping[catalog].append(operator)
    return catalog_to_operator_mapping


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

    catalog_to_operator_mapping = group_operators_by_catalog(args.catalog_operators)

    # For each catalog, create a fragment image
    for catalog_name, operators in catalog_to_operator_mapping.items():
        catalog_path = args.repo_path / "catalogs"
        fragment_image = create_fragment_image(
            catalog_path, catalog_name, operators, args
        )
        output_images[catalog_name] = fragment_image

    LOGGER.info("Fragment images created: %s", output_images)

    # Save the results to a file
    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(output_images, f)


if __name__ == "__main__":  # pragma: no cover
    main()
