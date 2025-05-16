"""
A module responsible for automated release of bundle to the FBC catalog.
"""

import argparse
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from operatorcert import utils
from operatorcert.logger import setup_logger
from operatorcert.operator_repo import Bundle, Operator, Repo
from ruamel.yaml import YAML

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Inject a bundle into FBC.")

    parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to the repository with operators and catalogs",
    )
    parser.add_argument(
        "--bundle-pullspec", type=str, help="A pullspec of bundle image."
    )
    parser.add_argument(
        "--operator-name",
        type=str,
        help="A name of operator that is going to be modified.",
    )
    parser.add_argument(
        "--operator-version",
        type=str,
        help="A version of operator that is going to be modified.",
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


class CatalogTemplate(ABC):
    """
    Abstract class for base catalog template.
    """

    def __init__(
        self,
        operator: Operator,
        template_type: str,
        template_name: str,
        catalog_names: list[str],
        **_: Any,
    ):
        self.operator = operator
        self.template_name = template_name
        self.template_type = template_type
        self.catalog_names = catalog_names

        self._template: dict[str, Any] = {}
        self.template_path = self.template_dir / self.template_name

        # A cache for opm commands
        self._cmd_cache: dict[str, subprocess.CompletedProcess[bytes]] = {}

    @property
    def template_dir(self) -> Path:
        """
        Get a directory of the template and create it if it doesn't exist.

        Returns:
            Path: A path to the directory of the template.
        """
        path = self.operator.root / "catalog-templates"

        # Create the directory if it doesn't exist
        os.makedirs(path, exist_ok=True)

        return path

    def exists(self) -> bool:
        """
        Check if the template exists by template path.

        Returns:
            bool: A boolean value indicating if the template exists.
        """
        return os.path.exists(self.template_path)

    @property
    def template(self) -> dict[str, Any]:
        """
        Get the template content. Load it from the file if it's not loaded yet.

        Returns:
            dict[str, Any]: A template object.
        """
        if not self._template:
            with open(self.template_path, "r", encoding="utf8") as f:
                self._template = YAML().load(f)
        return self._template

    def save(self) -> None:
        """
        Save the template to the file.
        """
        with open(self.template_path, "w", encoding="utf8") as f:
            yaml = YAML()
            yaml.explicit_start = True
            yaml.dump(self.template, f)

    @abstractmethod
    def create(
        self, release_config: dict[str, Any], bundle_pullspec: str, bundle: Bundle
    ) -> None:
        """
        Abstract method to create a new catalog template.
        """

    @abstractmethod
    def amend(
        self, release_config: dict[str, Any], bundle_pullspec: str, bundle: Bundle
    ) -> None:
        """
        Abstract method to amend an existing catalog template.
        """

    def add_new_bundle(
        self, release_config: dict[str, Any], bundle_pullspec: str, bundle: Bundle
    ) -> None:
        """
        Add a new bundle to the catalog template.

        Args:
            release_config (dict[str, Any]): A release configuration for the bundle.
            bundle_pullspec (str): A pullspec of the bundle image.
            bundle (Bundle): A bundle object.
        """
        if self.exists():
            self.amend(release_config, bundle_pullspec, bundle)
        else:
            self.create(release_config, bundle_pullspec, bundle)

    def render(self) -> None:
        """
        Render the catalog from the template using opm.
        """
        base_command = [
            "opm",
            "alpha",
            "render-template",
            self.template_type,
            "-o",
            "yaml",
            str(self.template_path),
        ]

        for catalog in self.catalog_names:
            extra_args = self._render_template_extra_args(catalog)
            command = base_command + extra_args

            LOGGER.info(
                f"Rendering catalog '{catalog}' from template %s", self.template_path
            )
            response = self.run_cmd_with_cache(command)
            catalog_path = (
                self.operator.repo.root
                / "catalogs"
                / catalog
                / self.operator.operator_name
            )
            os.makedirs(catalog_path, exist_ok=True)
            with open(catalog_path / "catalog.yaml", "w", encoding="utf8") as f:
                f.write(response.stdout.decode("utf-8"))

    def run_cmd_with_cache(
        self, command: list[Any]
    ) -> subprocess.CompletedProcess[bytes]:
        """
        Run a command with caching. In case the command was already run,
        with the same arguments, return the cached result.

        Args:
            command (list[str]): A command to run.

        Returns:
            subprocess.CompletedProcess[bytes]: Command output.
        """
        cache_key = " ".join(command)
        if cache_key in self._cmd_cache:
            LOGGER.debug("Using cached command: %s", command)
            return self._cmd_cache[cache_key]

        response = utils.run_command(command)
        self._cmd_cache[cache_key] = response
        return response

    def _render_template_extra_args(self, catalog: str) -> list[str]:
        """
        Get extra command line arguments for the template rendering.

        Args:
            catalog (str): Name of the catalog.

        Returns:
            list[str]: A list of extra command line arguments for the rendering.
        """
        extra_args = []
        extra_args.extend(self._bundle_object_to_csv_metada(catalog))
        return extra_args

    def _bundle_object_to_csv_metada(self, catalog: str) -> list[str]:
        """
        A buddle object to CSV metadata migration is needed for
        catalogs with version >= 4.17.

        Args:
            catalog (str): A name of the catalog.

        Returns:
            list[str]: command line arguments for the migration.
        """
        if not utils.is_catalog_v4_17_plus(catalog):
            return []
        return ["--migrate-level", "bundle-object-to-csv-metadata"]


class BasicTemplate(CatalogTemplate):
    """
    Class for basic catalog template.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["template_type"] = "basic"
        super().__init__(*args, **kwargs)

    @staticmethod
    def create_basic_channel_entry(
        release_config: dict[str, Any], bundle: Bundle
    ) -> dict[str, Any]:
        """
        Create a basic channel entry with a new bundle.

        Args:
            release_config (dict[str, Any]): A release configuration for the bundle.
            bundle (Bundle): A bundle object to create a channel entry for.

        Returns:
            dict[str, Any]: A channel entry for the basic template.
        """
        channel_entry = {"name": bundle.csv["metadata"]["name"]}

        if "replaces" in release_config:
            channel_entry["replaces"] = release_config["replaces"]
        if "skips" in release_config:
            channel_entry["skips"] = release_config["skips"]
        if "skipRange" in release_config:
            channel_entry["skipRange"] = release_config["skipRange"]
        return channel_entry

    def create(
        self, release_config: dict[str, Any], bundle_pullspec: str, bundle: Bundle
    ) -> None:
        """
        Create a new basic template and add a new bundle to it based on
        the release configuration.

        Args:
            release_config (dict[str, Any]): A release configuration for the bundle.
            bundle_pullspec (str): A pullspec of the bundle image.
            bundle (Bundle): A bundle object to be added to the template.
        """
        LOGGER.info("Creating a new basic template %s", self.template_name)
        channels = []
        for channel in release_config["channels"]:
            channels.append(
                {
                    "schema": "olm.channel",
                    "name": channel,
                    "package": self.operator.operator_name,
                    "entries": [
                        self.create_basic_channel_entry(release_config, bundle)
                    ],
                }
            )
        package = {
            "schema": "olm.package",
            "name": self.operator.operator_name,
            "defaultChannel": channels[0]["name"],
        }
        bundle_obj = {"schema": "olm.bundle", "image": bundle_pullspec}

        self._template = {
            "schema": "olm.template.basic",
            "entries": [package] + channels + [bundle_obj],
        }

    @staticmethod
    def add_bundle_if_not_present(
        template: dict[str, Any], bundle_pullspec: str
    ) -> None:
        """
        Add a bundle to the template if it's not present.

        Args:
            template (dict[str, Any]): A template object.
            bundle_pullspec (str): A pullspec of the bundle image.
        """
        for item in template["entries"]:
            if item["schema"] == "olm.bundle" and item["image"] == bundle_pullspec:
                return
        template["entries"].append(
            {
                "schema": "olm.bundle",
                "image": bundle_pullspec,
            }
        )

    def add_channels_if_not_present(self, release_config: dict[str, Any]) -> None:
        """
        Add channels to the template if they are not present.
        A channel is added as a placeholder for a new bundle.

        Args:
            release_config (dict[str, Any]): A release configuration for the bundle.
        """
        current_channels = [
            item["name"]
            for item in self.template["entries"]
            if item["schema"] == "olm.channel"
        ]
        for channel in release_config["channels"]:
            if channel in current_channels:
                continue
            self.template["entries"].append(
                {
                    "schema": "olm.channel",
                    "name": channel,
                    "package": self.operator.operator_name,
                    "entries": [],
                }
            )

    def amend(
        self, release_config: dict[str, Any], bundle_pullspec: str, bundle: Bundle
    ) -> None:
        """
        Amend the basic template by adding a new bundle to it.

        Args:
            release_config (dict[str, Any]): A release configuration for the bundle.
            bundle_pullspec (str): A pullspec of the bundle image.
            bundle (Bundle): A bundle object to be added to the template.
        """
        LOGGER.info("Amending basic template %s", self.template_name)
        self.add_channels_if_not_present(release_config)
        self.add_bundle_if_not_present(self.template, bundle_pullspec)
        channels_names = release_config["channels"]
        for item in self.template["entries"]:
            if item["schema"] == "olm.channel" and item["name"] in channels_names:
                new_entry = self.create_basic_channel_entry(release_config, bundle)
                if new_entry not in item["entries"]:
                    item["entries"].append(new_entry)


class SemverTemplate(CatalogTemplate):
    """
    Class for semver catalog template.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        kwargs["template_type"] = "semver"
        super().__init__(*args, **kwargs)

    def create(
        self, release_config: dict[str, Any], bundle_pullspec: str, _: Bundle
    ) -> None:
        """
        Create a new semver template and add a new bundle to it based on
        the release configuration.

        Args:
            release_config (dict[str, Any]): A release configuration for the bundle.
            bundle_pullspec (str): A pullspec of the bundle image.
            _ (Bundle): A bundle object to be added to the template.
        """
        LOGGER.info("Creating a new semver template %s", self.template_name)
        self._template = {
            "Schema": "olm.semver",
            "GenerateMajorChannels": True,
            "GenerateMinorChannels": True,
        }
        for channel in release_config["channels"]:
            self._template[channel] = {"Bundles": [{"Image": bundle_pullspec}]}

    def amend(
        self, release_config: dict[str, Any], bundle_pullspec: str, _: Bundle
    ) -> None:
        """
        Amend the semver template by adding a new bundle to it.

        Args:
            release_config (dic[str,Any]): A release configuration for the bundle.
            bundle_pullspec (str): A pullspec of the bundle image.
            _ (Bundle): A bundle object to be added to the template.
        """
        LOGGER.info("Amending semver template %s", self.template_name)
        for channel in release_config["channels"]:
            if channel not in self.template:
                self.template[channel] = {"Bundles": []}
            new_bundle = {"Image": bundle_pullspec}
            if new_bundle not in self.template[channel]["Bundles"]:
                self.template[channel]["Bundles"].append({"Image": bundle_pullspec})


def get_catalog_mapping(ci_file: dict[str, Any], template_name: str) -> Any:
    """
    Get a catalog mapping for a specific template.

    Args:
        ci_file (dict[str, Any]): A content of the ci.yaml file.
        template_name (str): A name of the template to get a mapping for.

    Returns:
        Optional[dict[str, Any]]: A catalog mapping for the template.
    """
    fbc = ci_file.get("fbc", {})
    for mapping in fbc.get("catalog_mapping", []) or []:
        if mapping["template_name"] == template_name:
            return mapping
    return None


def release_bundle_to_fbc(args: argparse.Namespace, bundle: Bundle) -> None:
    """
    Release a new bundle to a FBC catalog templates and render the catalog with
    a new changes.

    Args:
        args (argparse.Namespace): CLI arguments.
        bundle (Bundle): A bundle object to be released to FBC.

    Raises:
        ValueError: An exception is raised if the template type is unknown.
    """

    if not bundle.release_config:
        raise ValueError(
            f"Release config not found for {args.operator_name} {args.operator_version}"
        )

    # Update a catalog template
    for release_config_template in bundle.release_config["catalog_templates"]:
        template_name = release_config_template["template_name"]
        template_mapping = get_catalog_mapping(bundle.operator.config, template_name)
        if not template_mapping:
            raise ValueError(
                f"Template mapping not found for '{template_name}' in ci.yaml."
            )

        template_class_map = {
            "olm.template.basic": BasicTemplate,
            "olm.semver": SemverTemplate,
        }
        template_class = template_class_map.get(template_mapping["type"])
        if not template_class:
            raise ValueError(
                f"Unknown template type '{template_mapping['type']}' in ci.yaml."
            )

        template: CatalogTemplate = template_class(bundle.operator, **template_mapping)

        template.add_new_bundle(release_config_template, args.bundle_pullspec, bundle)
        template.save()
        template.render()


def main() -> None:
    """
    Main function for the cli tool.
    """
    parser = setup_argparser()
    args = parser.parse_args()

    # Logging
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    operator_repo = Repo(args.repo_path)
    bundle = operator_repo.operator(args.operator_name).bundle(args.operator_version)

    release_bundle_to_fbc(args, bundle)


if __name__ == "__main__":  # pragma: no cover
    main()
