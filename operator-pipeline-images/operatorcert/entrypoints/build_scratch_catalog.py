"""Create a catalog image dockerfile and build catalog image."""

import argparse
import logging
import os
import tempfile
from typing import Any

import yaml
from operator_repo import Repo, Bundle
from operatorcert import buildah, opm
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        argparse.ArgumentParser: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Build a temporary scratch catalog and add a single bundle to it."
    )
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to the repository with operators and catalogs",
    )
    parser.add_argument("--operator-name", required=True, help="Operator name")
    parser.add_argument(
        "--bundle-version", required=True, help="Operator bundle version"
    )
    parser.add_argument(
        "--bundle-pullspec", required=True, help="Operator bundle pullspec"
    )
    parser.add_argument(
        "--repository-destination",
        required=True,
        help="Registry and repository where the image will be pushed including"
        "the tag",
    )
    parser.add_argument(
        "--authfile",
        default="~/.docker/config.json",
        help="A path to the authentication file",
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def generate_and_save_basic_template(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    template_path: str,
    package: str,
    default_channel: str,
    channel_name: str,
    csv_name: str,
    bundle_pullspec: str,
) -> Any:
    """
    Generate and save basic template into a file given the parameters.

    Args:
        template_path (str): A path to the file where the template will be saved
        package (str): A name of the package
        default_channel (str): A name of the default channel for the package
        channel_name (str): A name of the channel for the package
        csv_name (str): A name of the CSV resource
        bundle_pullspec (str): A pullspec of the bundle image

    Returns:
        Any: A path to the saved template
    """

    package_obj = {
        "schema": "olm.package",
        "name": package,
        "defaultChannel": default_channel,
    }
    channel = {
        "schema": "olm.channel",
        "package": package,
        "name": channel_name,
        "entries": [{"name": csv_name}],
    }

    bundles = {"schema": "olm.bundle", "image": bundle_pullspec}
    template = {
        "schema": "olm.template.basic",
        "entries": [package_obj, channel, bundles],
    }

    with open(template_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            template,
            f,
            explicit_start=True,
            indent=2,
        )

    return template_path


def build_and_push_catalog_image(
    bundle: Bundle, bundle_pullspec: str, repository_destination: str, authfile: Any
) -> None:
    """
    Build and push a catalog image with a single bundle.

    The function creates a temporary directory, generates a basic template and
    renders it to a catalog. Then it creates a Dockerfile for the catalog image,
    builds the image and pushes it to the repository.

    Args:
        bundle (Bundle): An instance of the Bundle class representing the bundle
            being added to the catalog
        bundle_pullspec (str): A pullspec of the bundle image
        repository_destination (str): A full path to the repository where the
            catalog image will be pushed
        authfile (Any): A path to the authentication file for the repository
            where the catalog image will be pushed
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = f"{tmpdir}/{bundle.metadata_operator_name}"
        os.mkdir(bundle_dir)

        template_path = os.path.join(tmpdir, "template.yaml")
        channel_name = list(bundle.channels)[0] if bundle.channels else "stable"
        default_channel = bundle.default_channel or channel_name

        generate_and_save_basic_template(
            template_path=template_path,
            package=bundle.metadata_operator_name,
            default_channel=default_channel,
            channel_name=channel_name,
            csv_name=bundle.csv["metadata"]["name"],
            bundle_pullspec=bundle_pullspec,
        )

        catalog_path = os.path.join(bundle_dir, "catalog.yaml")
        opm.render_template_to_catalog(template_path, catalog_path)

        dockerfile_path = opm.create_catalog_dockerfile(
            tmpdir, bundle.metadata_operator_name
        )
        buildah.build_image(dockerfile_path, tmpdir, repository_destination)
        buildah.push_image(repository_destination, authfile)


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

    repo = Repo(args.repo_path)
    bundle = repo.operator(args.operator_name).bundle(args.bundle_version)

    build_and_push_catalog_image(
        bundle,
        args.bundle_pullspec,
        args.repository_destination,
        args.authfile,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
