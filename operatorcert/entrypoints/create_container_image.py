"""Create ContainerImage resource in Pyxis"""

import argparse
import json
import logging
from datetime import datetime
from typing import Any, Dict
from urllib.parse import quote, urljoin

from operatorcert import pyxis
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="ContainerImage resource creator.")

    parser.add_argument(
        "--pyxis-url",
        default="https://pyxis.engineering.redhat.com",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument(
        "--isv-pid",
        help="isv_pid of the certification project from Red Hat Connect",
        required=True,
    )
    parser.add_argument(
        "--registry",
        help="Internal registry host",
        required=True,
    )
    parser.add_argument(
        "--repository",
        help="Repository name where bundle image is stored",
        required=True,
    )
    parser.add_argument(
        "--bundle-version",
        help="Operator bundle version",
        required=True,
    )
    parser.add_argument(
        "--docker-image-digest",
        help="Container Image digest of related Imagestream",
        required=True,
    )
    parser.add_argument(
        "--skopeo-result",
        help="File with result of `skopeo inspect` running against image"
        " represented by ContainerImage to be created",
        required=True,
    )
    parser.add_argument(
        "--output-file", help="Path to a json file where results will be stored"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def check_if_image_already_exists(args: Any) -> Any:
    """
    Check if image with given docker_image_digest and isv_pid already exists

    Args:
        args (Any): CLI arguments

    Returns:
        Any: Container image object if image already exists, else None
    """
    # quote is needed to urlparse the quotation marks
    filter_str = quote(
        f'isv_pid=="{args.isv_pid}";'
        f'docker_image_digest=="{args.docker_image_digest}";'
        f"not(deleted==true)"
    )

    check_url = urljoin(args.pyxis_url, f"v1/images?page_size=1&filter={filter_str}")

    # Get the list of the ContainerImages with given parameters
    rsp = pyxis.get(check_url)
    rsp.raise_for_status()

    query_results = rsp.json()["data"]

    if len(query_results) == 0:
        LOGGER.info(
            "Image with given docker_image_digest and isv_pid doesn't exist yet"
        )
        return None

    LOGGER.info(
        "Image with given docker_image_digest and isv_pid already exists."
        "Skipping the image creation."
    )
    return query_results[0]


def prepare_parsed_data(skopeo_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare parsed_data for ContainerImage

    Args:
        skopeo_result (Dict[str, Any]): Skopeo inspect result

    Returns:
        Dict[str, Any]: Parsed data section of ContainerImage
    """
    parsed_data = {
        "docker_version": skopeo_result.get("DockerVersion", ""),
        "layers": skopeo_result.get("Layers", []),
        "architecture": skopeo_result.get("Architecture", ""),
        "env_variables": skopeo_result.get("Env", []),
    }

    return parsed_data


def get_image_size(skopeo_result: Dict[str, Any]) -> int:
    """
    Get image size from skopeo result

    Args:
        skopeo_result (Dict[str, Any]): Skopeo inspect result

    Returns:
        int: Image size in bytes
    """
    size = 0
    for layer in skopeo_result.get("LayersData", []):
        size += layer.get("Size") or 0
    return size


def create_container_image(args: Any, skopeo_result: Dict[str, Any]) -> Any:
    """
    Create ContainerImage resource in Pyxis

    Args:
        args (Any): CLI arguments
        skopeo_result (Dict[str, Any]): Skopeo inspect result

    Returns:
        Any: Pyxis POST response
    """
    LOGGER.info("Creating new container image")

    date_now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
    parsed_data = prepare_parsed_data(skopeo_result)

    upload_url = urljoin(args.pyxis_url, "v1/images")
    container_image_payload = {
        "isv_pid": args.isv_pid,
        "repositories": [
            {
                "published": False,
                "registry": args.registry,
                "repository": args.repository,
                "push_date": date_now,
                "tags": [
                    {
                        "added_date": date_now,
                        "name": args.bundle_version,
                    },
                    {
                        "added_date": date_now,
                        "name": "latest",
                    },
                ],
            }
        ],
        "certified": True,
        "docker_image_digest": args.docker_image_digest,
        "image_id": args.docker_image_digest,
        "architecture": parsed_data["architecture"],
        "parsed_data": parsed_data,
        "sum_layer_size_bytes": get_image_size(skopeo_result),
    }

    return pyxis.post(upload_url, container_image_payload)


def main() -> None:  # pragma: no cover
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)

    with open(args.skopeo_result, encoding="utf-8") as json_file:
        skopeo_result = json.load(json_file)

    image = check_if_image_already_exists(args)

    if not image:
        image = create_container_image(args, skopeo_result)

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as output_file:
            json.dump(image, output_file)


if __name__ == "__main__":  # pragma: no cover
    main()
