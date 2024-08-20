"""Onboard operator to File-based catalog (FBC) migration tool"""

import argparse
import logging
import os
import sys
from typing import Any, Dict, Optional

import requests
import yaml
from operator_repo import Operator, Repo
from operatorcert.logger import setup_logger
from operatorcert.utils import run_command

LOGGER = logging.getLogger("operator-cert")

CATALOG_TEMPLATES_DIR = "catalog-templates"


def setup_argparser() -> Any:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Onboarding tool for File-based catalog migration."
    )

    parser.add_argument(
        "--repo-root",
        default="./",
        help="Path to the root of the repository",
    )
    parser.add_argument(
        "--operator-name",
        help="Name of the operator",
        required=True,
    )
    parser.add_argument(
        "--cache-dir",
        help="A path to the directory where the catalog cache will be stored",
        default=".catalog_cache",
    )
    parser.add_argument(
        "--stage",
        help="Run a onboarding with a stage catalogs",
        action="store_true",
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def get_supported_catalogs(organization: str, stage: bool) -> Any:
    """
    Get supported catalogs for the given organization

    Args:
        organization (str): Name of the organization as stated in the API

    Returns:
        Any: A list of supported catalogs with their versions and pullspecs
    """
    response = requests.get(
        "https://catalog.redhat.com/api/containers/v1/operators/indices",
        params={
            # By adding any eol version (v4.5) we force Pyxis to filter
            # only supported versions
            "filter": f"organization=={organization}",
            "ocp_versions_range": "v4.5",
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json().get("data", [])
    if stage:
        for catalog in data:
            catalog["path"] = catalog["path"].replace(
                "registry.redhat.io", "registry.stage.redhat.io"
            )
    return data


def opm_cache(image: str) -> bytes:
    """
    Run opm to render a catalog and cache it

    Args:
        image (str): Image catalog pullspec

    Returns:
        bytes: An output of the opm command
    """
    LOGGER.debug("Building cache for %s", image)
    output = run_command(["opm", "render", "-o", "yaml", image])
    return output.stdout


def build_cache(version: str, image: str, cache_dir: str) -> None:
    """
    Build a local cache of the catalog to avoid opm renders

    Args:
        version (str): A catalog ocp version
        image (str): Catalog image pullspec
        cache_dir (str): A directory where the cache will be stored
    """
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    catalog_cache = os.path.join(cache_dir, f"{version}.yaml")
    if os.path.exists(catalog_cache):
        LOGGER.debug("Catalog cache exists for %s", version)
        return
    catalog = opm_cache(image)
    with open(catalog_cache, "wb") as f:
        f.write(catalog)


def get_base_template_from_catalog(
    operator_name: str, catalog: Any
) -> Optional[Dict[str, Any]]:
    """
    Generate a basic template from file based catalog. The function filters
    out operator from a catalog and removes unnecessary fields and
    generate a basic template.

    Args:
        operator_name (str): Operator name for which the template is generated
        catalog (Any): A file based catalog with all operators

    Returns:
        Optional[Dict[str, Any]]: A basic template for the operator.
        In case an operator is not present in a catalog, None is returned
    """
    # Filter out the operator items from the catalog
    # Items can be identified by the name or package field
    operator_items = (
        item
        for item in catalog
        if item.get("name") == operator_name or item.get("package") == operator_name
    )

    entries = []

    for item in operator_items:
        if item.get("schema") == "olm.bundle":
            # Keep only image and schema fields - rest can be extracted from the image
            # when rendering the template
            entries.append({"schema": item["schema"], "image": item["image"]})
        else:
            # Keep only the non-bundle items - packages, channels, etc.
            entries.append(item)
    if not entries:
        return None
    return {"schema": "olm.template.basic", "entries": entries}


def create_catalog_template_dir_if_not_exists(operator: Any) -> str:
    """
    If the template directory does not exist, create it

    Args:
        operator (Any): Operator object

    Returns:
        str: Path to the template directory
    """
    template_dir = os.path.join(operator.root, CATALOG_TEMPLATES_DIR)
    if os.path.exists(template_dir):
        LOGGER.info("FBC template directory already exists at %s", template_dir)
        user_input = input("FBC template directory already exists. Overwrite? [y/n]: ")
        if user_input.lower() != "y":
            sys.exit(0)
    if not os.path.exists(template_dir):
        LOGGER.info("Creating template directory at %s", template_dir)
        os.makedirs(template_dir)
    return template_dir


def generate_and_save_base_templates(
    version: str, operator_name: str, cache_dir: str, template_dir: str
) -> Optional[Dict[str, Any]]:
    """
    Generate and save basic templates for a given operator and version

    Args:
        version (str): OCP catalog version
        operator_name (str): Operator name
        cache_dir (str): A directory where the catalog cache is stored
        template_dir (str): A directory where the templates will be stored

    Returns:
        Optional[Dict[str, Any]]: A basic template for the operator.
        In case an operator is not present in a catalog, None is returned
    """
    with open(os.path.join(cache_dir, f"{version}.yaml"), "r", encoding="utf8") as f:
        catalog = yaml.safe_load_all(f)
        basic_template = get_base_template_from_catalog(operator_name, catalog)
    if not basic_template:
        LOGGER.info(
            "An operator %s not found in the catalog %s", operator_name, version
        )
        return basic_template

    template_path = os.path.join(template_dir, f"v{version}.yaml")
    with open(template_path, "w", encoding="utf8") as f:
        yaml.safe_dump(basic_template, f, explicit_start=True, indent=2)

    LOGGER.info("Template for %s saved to %s", version, template_path)
    return basic_template


def update_operator_config(operator: Operator) -> None:
    """
    Switch operator config to FBC

    Args:
        operator (Operator): Operator object
    """
    config = operator.config
    config["fbc"] = {
        "enabled": True,
    }
    # Update graph is not needed anymore for FBC
    config.pop("updateGraph", None)

    config_path = os.path.join(operator.root, operator.CONFIG_FILE)
    with open(config_path, "w", encoding="utf8") as f:
        yaml.safe_dump(config, f, explicit_start=True)


def render_fbc_from_template(operator: Operator, version: str) -> None:
    """
    Render catalog from templates

    Args:
        operator (Operator): Operator object
    """
    output = run_command(
        [
            "opm",
            "alpha",
            "render-template",
            "basic",
            "-o",
            "yaml",
            os.path.join(operator.root, CATALOG_TEMPLATES_DIR, f"v{version}.yaml"),
        ],
        cwd=operator.root,
    )

    catalogs_path = os.path.join(operator.root, "../../catalogs")
    catalogs_path = os.path.abspath(catalogs_path)
    operator_in_catalogs_path = os.path.join(
        catalogs_path, f"v{version}/{operator.operator_name}"
    )

    if not os.path.exists(operator_in_catalogs_path):
        os.makedirs(operator_in_catalogs_path)

    with open(
        os.path.join(operator_in_catalogs_path, "catalog.yaml"), "w", encoding="utf8"
    ) as f:
        catalog_content = yaml.safe_load_all(output.stdout)
        yaml.safe_dump_all(catalog_content, f, explicit_start=True, indent=2)

    LOGGER.info("FBC rendered to %s", operator_in_catalogs_path)


def onboard_operator_to_fbc(
    operator_name: str, repository: Repo, cache_dir: str, stage: bool
) -> None:
    """
    Onboard operator to FBC and generates templates, catalogs and config

    Args:
        operator_name (str): Name of the operator that will be onboarded
        repository (Repo): A repository object with operators
        cache_dir (str): A directory where the catalog cache will be stored
    """
    organization = repository.config.get("organization")
    supported_catalogs = get_supported_catalogs(organization, stage)
    supported_versions = sorted(
        [catalog.get("ocp_version") for catalog in supported_catalogs]
    )
    LOGGER.info(
        "Generating FBC templates for following versions: %s", supported_versions
    )

    operator = repository.operator(operator_name)
    template_dir = create_catalog_template_dir_if_not_exists(operator)

    for catalog in supported_catalogs:
        version = catalog.get("ocp_version")
        image = catalog.get("path")
        LOGGER.info("Processing catalog: v%s", version)

        build_cache(version, image, cache_dir)
        template = generate_and_save_base_templates(
            version, operator_name, cache_dir, template_dir
        )
        if template:
            # Render a catalog only if basic template was generated
            LOGGER.info("Rendering FBC from templates")
            render_fbc_from_template(operator, version)

    LOGGER.info("Updating operator config")
    update_operator_config(operator)


def main() -> None:  # pragma: no cover
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)

    repo = Repo(args.repo_root)
    onboard_operator_to_fbc(args.operator_name, repo, args.cache_dir, args.stage)


if __name__ == "__main__":  # pragma: no cover
    main()
