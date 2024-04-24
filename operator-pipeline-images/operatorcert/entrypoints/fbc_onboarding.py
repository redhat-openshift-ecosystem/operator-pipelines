"""Onboard operator to File-based catalog (FBC) migration tool"""

import argparse
import logging
import os
import sys
from typing import Any, Dict, List, Tuple

import requests
import yaml
from operator_repo import Operator, Repo
from operatorcert.logger import setup_logger
from operatorcert.utils import run_command

LOGGER = logging.getLogger("operator-cert")

COMPOSITE_TEMPLATE_CATALOGS = "catalogs.yaml"
COMPOSITE_TEMPLATE_CONTRIBUTIONS = "composite-config.yaml"
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
    output = run_command(["opm", "render", "-o", "yaml", "--migrate", image])
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


def get_base_template_from_catalog(operator_name: str, catalog: Any) -> List[Any]:
    """
    Generate a basic template from file based catalog. The function filters
    out operator from a catalog and removes unnecessary fields and
    generate a basic template.

    Args:
        operator_name (str): Operator name for which the template is generated
        catalog (Any): A file based catalog with all operators

    Returns:
        List[Any]: List of basic template items for a given operator
    """
    # Filter out the operator items from the catalog
    # Items can be identified by the name or package field
    operator_items = list(
        filter(
            lambda x: x.get("name") == operator_name
            or x.get("package") == operator_name,
            catalog,
        )
    )

    # Keep only the non-bundle items - packages, channels, etc.
    non_bundles = list(
        filter(lambda x: x.get("schema") != "olm.bundle", operator_items)
    )

    bundles = list(filter(lambda x: x.get("schema") == "olm.bundle", operator_items))

    # Keep only image and schema fields - rest can be extracted from the image
    # when rendering the template
    bundles = [
        {"schema": bundle.get("schema"), "image": bundle.get("image")}
        for bundle in bundles
    ]

    return non_bundles + bundles


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
) -> None:
    """
    Generate and save basic templates for a given operator and version

    Args:
        version (str): OCP catalog version
        operator_name (str): Operator name
        cache_dir (str): A directory where the catalog cache is stored
        template_dir (str): A directory where the templates will be stored
    """
    with open(os.path.join(cache_dir, f"{version}.yaml"), "r", encoding="utf8") as f:
        catalog = yaml.safe_load_all(f)
        basic_template = get_base_template_from_catalog(operator_name, catalog)

    template_path = os.path.join(template_dir, f"v{version}.yaml")
    with open(template_path, "w", encoding="utf8") as f:
        yaml.safe_dump_all(basic_template, f, explicit_start=True, indent=2)

    LOGGER.info("Template for %s saved to %s", version, template_path)


def generate_composite_templates(
    operator: Operator, catalog_versions: List[str]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Generate a composite template for given operator and all supported versions

    Args:
        operator (Operator): A operator object
        catalog_versions (List[str]): List of supported catalog versions

    Returns:
        Tuple[Dict, Dict]: catalog and contributions templates
    """
    catalogs = [
        {
            "name": f"v{version}",
            "destination": {
                "workingDir": f"../../catalogs/v{version}",
            },
            "builders": ["olm.builder.basic", "olm.builder.semver"],
        }
        for version in catalog_versions
    ]
    composite_catalogs = {
        "schema": "olm.composite.catalogs",
        "catalogs": catalogs,
    }

    components = [
        {
            "name": f"v{version}",
            "destination": {
                "path": operator.operator_name,
            },
            "strategy": {
                "name": "basic",
                "template": {
                    "schema": "olm.builder.basic",
                    "config": {
                        "input": f"{CATALOG_TEMPLATES_DIR}/v{version}.yaml",
                        "output": "catalog.yaml",
                    },
                },
            },
        }
        for version in catalog_versions
    ]

    contributions = {"schema": "olm.composite", "components": components}
    return composite_catalogs, contributions


def generate_and_save_composite_templates(
    operator: Operator, catalog_versions: List[str]
) -> None:
    """
    Generate and save composite templates for given operator and all supported versions

    Args:
        operator (Operator): A operator object
        catalog_versions (List[str]): List of supported catalog versions
    """
    catalog, contributions = generate_composite_templates(operator, catalog_versions)
    with open(
        os.path.join(operator.root, COMPOSITE_TEMPLATE_CATALOGS), "w", encoding="utf8"
    ) as f:
        yaml.safe_dump(catalog, f, explicit_start=True)
    with open(
        os.path.join(operator.root, COMPOSITE_TEMPLATE_CONTRIBUTIONS),
        "w",
        encoding="utf8",
    ) as f:
        yaml.safe_dump(contributions, f, explicit_start=True)


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


def render_fbc_from_template(operator: Operator) -> None:
    """
    Render catalog from templates

    Args:
        operator (Operator): Operator object
    """
    run_command(
        [
            "opm",
            "alpha",
            "render-template",
            "composite",
            "-f",
            COMPOSITE_TEMPLATE_CATALOGS,
            "-c",
            COMPOSITE_TEMPLATE_CONTRIBUTIONS,
        ],
        cwd=operator.root,
    )
    catalog_path = os.path.join(operator.root, "../../catalogs")
    catalog_path = os.path.abspath(catalog_path)
    LOGGER.info("FBC rendered to %s", catalog_path)


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
    supported_versions = [catalog.get("ocp_version") for catalog in supported_catalogs]

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
        generate_and_save_base_templates(
            version, operator_name, cache_dir, template_dir
        )

    LOGGER.info("Generating composite templates")
    generate_and_save_composite_templates(operator, supported_versions)

    LOGGER.info("Rendering FBC from templates")
    render_fbc_from_template(operator)

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
