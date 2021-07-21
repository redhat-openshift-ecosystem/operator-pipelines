import argparse
import logging
import os
from typing import Any

import yaml


class AnnotationFileNotFound(Exception):
    """
    Exception for missing bundle annotation file
    """


def setup_argparser() -> Any:
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


def read_annotation(annotation_path: str) -> Any:
    """
    Read annotation from annotation yaml file

    Args:
        annotation_path (str): Path to annotation file

    Returns:
        Any: Bundle annotation dictionary
    """
    with open(annotation_path, "r") as annotation_file:
        content = yaml.safe_load(annotation_file)

    return content.get("annotations", {})


def check_annotation_file(bundle_path: str) -> str:
    """
    Check availability of annotation file. The file can have both .yml
    and .yaml extension.

    Args:
        bundle_path (str): Path to bundle root directory

    Raises:
        AnnotationFileNotFound: Exception is raised when annotation file is missing

    Returns:
        str: Full path to bundle annotation file
    """
    possible_paths = ["metadata/annotations.yaml", "metadata/annotations.yml"]
    for annotation_path in possible_paths:
        full_path = os.path.join(bundle_path, annotation_path)
        if os.path.exists(full_path):
            logging.debug(f"Found the annotation file: {annotation_path}")
            return full_path

    raise AnnotationFileNotFound(
        f"Annotation file is not available in any of these locations {possible_paths}"
    )


def generate_dockerfile_content(args: Any) -> str:
    """
    Generate a Dockerfile based on bundle metadata

    The content is based on what opm tool generates.

    Args:
        args (Any): Argparser argument

    Returns:
        str: Content of generated Dockerfile
    """
    logging.debug("Generating a dockerfile...")
    dockerfile_content = "FROM scratch\n\n"

    annotation_file_path = check_annotation_file(args.bundle_path)
    annotations = read_annotation(annotation_file_path)

    for annotation_key, annotation_value in annotations.items():
        dockerfile_content += f"LABEL {annotation_key}={annotation_value}\n"

    dockerfile_content += "\n"

    manifests_path = annotations["operators.operatorframework.io.bundle.manifests.v1"]
    dockerfile_content += f"COPY {manifests_path} /manifests/\n"

    metadata_path = annotations["operators.operatorframework.io.bundle.metadata.v1"]
    dockerfile_content += f"COPY {metadata_path} /metadata/\n"

    dockerfile_content += "\n"

    return dockerfile_content


def main() -> None:
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"

    logging.basicConfig(level=log_level)
    dockerfile_content = generate_dockerfile_content(args)

    logging.info(f"Storing dockerfile: {args.destination}")
    with open(args.destination, "w") as dockerfile_file:
        dockerfile_file.write(dockerfile_content)


if __name__ == "__main__":
    main()
