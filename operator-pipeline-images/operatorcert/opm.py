"""A collection of functions for working with Operator Package Manager (OPM)"""

import logging
import os
from pathlib import Path

from operatorcert.utils import run_command

LOGGER = logging.getLogger("operator-cert")


def create_catalog_dockerfile(catalog_path: Path, catalog_name: str) -> Path:
    """
    Generate a Dockerfile using opm for a given catalog.

    Args:
        catalog_path (Path): Path to a catalogs direcotory
        catalog_name (str): Name of the catalog in the catalogs directory

    Returns:
        Path: A Dockerfile path for the given catalog
    """
    dockerfile_path = catalog_path / f"{catalog_name}.Dockerfile"
    if dockerfile_path.exists():
        LOGGER.warning("Dockerfile already exists: %s. Removing...", dockerfile_path)
        os.remove(dockerfile_path)
    cmd = [
        "opm",
        "generate",
        "dockerfile",
        str(catalog_path / catalog_name),
    ]
    LOGGER.debug("Creating dockerfile: %s", catalog_name)
    run_command(cmd)
    return dockerfile_path


def render_template_to_catalog(template_path: str, catalog_path: str) -> None:
    """
    Render a basic template to a catalog in yaml format.

    Args:
        template_path (str): A path to a template file
        catalog_path (str): A path to a catalog file to save the rendered template

    """
    command = ["opm", "alpha", "render-template", "basic", "-o", "yaml", template_path]
    response = run_command(command)

    with open(catalog_path, "w", encoding="utf-8") as f:
        f.write(response.stdout.decode("utf-8"))
