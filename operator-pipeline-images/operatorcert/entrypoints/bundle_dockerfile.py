import argparse
import logging
import pathlib
from typing import Any

import operatorcert
from operatorcert.logger import setup_logger
from operatorcert.utils import store_results

LOGGER = logging.getLogger("operator-cert")


class AnnotationFileNotFound(Exception):
    """
    Exception for missing bundle annotation file
    """


def setup_argparser() -> argparse.ArgumentParser:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Bundle dockerfile generator.")

    parser.add_argument(
        "--bundle-path", required=True, help="Location of operator bundle"
    )
    parser.add_argument(
        "--destination", default="Dockerfile", help="Location of new bundle Dockerfile"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def generate_dockerfile_content(args: Any) -> str:
    """
    Generate a Dockerfile based on bundle metadata

    The content is based on what opm tool generates.

    Args:
        args (Any): Argparser argument

    Returns:
        str: Content of generated Dockerfile
    """
    LOGGER.debug("Generating a dockerfile...")
    dockerfile_content = "FROM scratch\n\n"

    bundle_path = pathlib.Path(args.bundle_path)
    annotations = operatorcert.get_bundle_annotations(bundle_path)

    for annotation_key, annotation_value in annotations.items():
        dockerfile_content += f"LABEL {annotation_key}='{annotation_value}'\n"

    dockerfile_content += "\n"

    manifests_path = annotations["operators.operatorframework.io.bundle.manifests.v1"]
    dockerfile_content += f"COPY {manifests_path} /manifests/\n"

    metadata_path = annotations["operators.operatorframework.io.bundle.metadata.v1"]
    dockerfile_content += f"COPY {metadata_path} /metadata/\n"

    dockerfile_content += "\n"

    return dockerfile_content


def main() -> None:  # pragma: no cover
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"

    setup_logger(level=log_level)
    dockerfile_content = generate_dockerfile_content(args)

    results = {args.destination: dockerfile_content}
    store_results(results)


if __name__ == "__main__":  # pragma: no cover
    main()
