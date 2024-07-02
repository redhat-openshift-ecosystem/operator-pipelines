"""Module for building and pushing images using buildah."""

import logging
import os
from typing import Any

from operatorcert.utils import run_command

LOGGER = logging.getLogger("operator-cert")


def build_image(dockerfile_path: str, context: str, output_image: str) -> Any:
    """
    Build an image using buildah using given dockerfile and context.

    Args:
        dockerfile_path (str): Path to a dockerfile
        context (str): Build context directory
        output_image (str): A name of the output image

    Returns:
        Any: Command output
    """
    cmd = [
        "buildah",
        "bud",
        "--format",
        "docker",
        "-f",
        dockerfile_path,
        "-t",
        output_image,
        context,
    ]
    LOGGER.info("Building image: %s", output_image)
    return run_command(cmd)


def push_image(image: str, authfile: str) -> Any:
    """
    Push an image to a registry using buildah.

    Args:
        image (str): A name of the image to push
        authfile (str): A path to the authentication file

    Returns:
        Any: Command output
    """
    authfile = os.path.expanduser(authfile)
    cmd = [
        "buildah",
        "push",
        "--authfile",
        authfile,
        image,
        f"docker://{image}",
    ]

    LOGGER.info("Pushing image: %s", image)
    return run_command(cmd)
