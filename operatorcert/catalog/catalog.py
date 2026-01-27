"""A module for working with catalog content."""

from typing import Any, Iterator, Optional

import yaml
from operatorcert.catalog.bundle import CatalogBundle
from operatorcert.catalog.channel import CatalogChannel
from operatorcert.catalog.package import CatalogPackage
from operatorcert.utils import run_command


class Catalog:
    """
    A class representing a catalog content. The catalog content is a list of
    objects representing different content types. The content types are defined
    by the schema of the content.

    The class parses the content and provides methods to work with the content.
    """

    def __init__(self, content: list[dict[str, Any]]):
        self.content = content
        self._content_types: dict[str, list[dict[str, Any]]] = {}

        self._packages: list[CatalogPackage] = []
        self._channels: list[CatalogChannel] = []
        self._bundles: list[CatalogBundle] = []

    @classmethod
    def from_file(cls, file_path: str) -> "Catalog":
        """
        Create a Catalog object from a file. The file should be an output
        of the OPM render command.

        Args:
            file_path (str): A path to a file with the catalog content.

        Returns:
            Catalog: A Catalog object.
        """
        with open(file_path, "r", encoding="utf8") as f:
            content = list(yaml.safe_load_all(f))

        return cls(content)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """
        An iterator for the catalog content.

        Returns:
            iter: An iterator for the catalog content.
        """
        return iter(self.content)

    @property
    def content_types(self) -> dict[str, list[dict[str, Any]]]:
        """
        A property to get content types from the catalog. A content type is
        defined by the schema of the content.

        Returns:
            dict[str, list]: A mapping of content types to the content.
        """
        if not self._content_types:
            for content in self:
                schema = content["schema"]
                if schema not in self._content_types:
                    self._content_types[schema] = []
                self._content_types[schema].append(content)
        return self._content_types

    def get_all_packages(self) -> list[CatalogPackage]:
        """
        Get all packages from the catalog.

        Returns:
            list[CatalogPackage]: A list of all packages in the catalog.
        """
        # Get all packages from the catalog
        if not self._packages:
            packages = self.content_types.get("olm.package", [])
            for package in packages:
                self._packages.append(CatalogPackage(package, self))
        return self._packages

    def get_package(self, package_name: str) -> Optional[CatalogPackage]:
        """
        Get a package from the catalog by its name.

        Args:
            package_name (str): A name of a package that should be retrieved.

        Returns:
            CatalogPackage: A package object for the provided package name.
        """
        # Get a package from the catalog
        for package in self.get_all_packages():
            if package.name == package_name:
                return package
        return None

    def get_all_channels(self) -> list[CatalogChannel]:
        """
        Get all channels from the catalog.

        Returns:
            list[CatalogChannel]: A list of all channels in the catalog.
        """
        # Get all channels from the catalog
        if not self._channels:
            channels = self.content_types.get("olm.channel", [])
            for channel in channels:
                self._channels.append(CatalogChannel(channel, self))
        return self._channels

    def get_channels(self, channel_name: str) -> list[CatalogChannel]:
        """
        Get channels from the catalog by their name.
        There can be multiple channels with the same name but in different packages.

        Args:
            channel_name (str): A name of a channel that should be retrieved.

        Returns:
            list[CatalogChannel]: A list of channels with the provided name.
        """
        # Get a channels from the catalog
        channels = []
        for channel in self.get_all_channels():
            if channel.name == channel_name:
                channels.append(channel)
        return channels

    def get_all_bundles(self) -> list[CatalogBundle]:
        """
        Get all bundles from the catalog.

        Returns:
            list[CatalogBundle]: A list of all bundles in the catalog.
        """
        # Get all bundles from the catalog
        if not self._bundles:
            for content in self.content:
                if content["schema"] == "olm.bundle":
                    self._bundles.append(CatalogBundle(content, self))
        return self._bundles

    def get_bundle(self, bundle_name: str) -> Optional[CatalogBundle]:
        """
        Get a bundle from the catalog by its name.

        Args:
            bundle_name (str): A name of a bundle that should be retrieved.

        Returns:
            CatalogBundle: A bundle object for the provided bundle name.
        """
        # Get a bundle from the catalog
        for bundle in self.get_all_bundles():
            if bundle.name == bundle_name:
                return bundle
        return None

    def get_bundles_by_package(self, package_name: str) -> list[CatalogBundle]:
        """
        Get bundles from the catalog by package name.

        Args:
            package_name (str): A name of a package for which bundles should be retrieved.

        Returns:
            list[CatalogBundle]: A list of bundles for the provided package name.
        """
        bundles = []
        for bundle in self.get_all_bundles():
            if bundle.package_name == package_name:
                bundles.append(bundle)
        return bundles


class CatalogImage:
    """
    A class representing a catalog image. The catalog image is an image that
    holds the catalog content. The class provides methods to work with the
    image and turn it into a Catalog object using the OPM tool.
    """

    def __init__(self, image: str):
        self.image = image

        self._catalog_content: Optional[Catalog] = None

    @property
    def catalog_content(self) -> Catalog:
        """
        A property to get the catalog content from the image.

        A method creates a Catalog object from the parsed content.

        Returns:
            Catalog: A Catalog object representing the catalog content.
        """
        if not self._catalog_content:
            self._catalog_content = Catalog(self._get_catalog_content())

        return self._catalog_content

    def _get_catalog_content(self) -> list[dict[str, Any]]:
        """
        Parse the catalog content from the image and return it as a list.

        Returns:
            list: A list of parsed catalog content.
        """
        # Get the catalog content from the image

        render_output = self._opm_render()
        return list(yaml.safe_load_all(render_output))

    def _opm_render(self) -> str:
        """
        Render the catalog image using OPM and return the output of the command.

        Returns:
            str: A string with the output of the OPM render command.
        """
        # Render the catalog image using OPM

        # opm requires an authfile to pull the image, use DOCKER_CONFIG environment variable
        # to override the default location of the authfile if needed
        command = ["opm", "render", "-o", "yaml", self.image]
        output = run_command(command)
        return output.stdout.decode("utf-8")

    def __str__(self) -> str:
        """A string representation of a catalog image."""
        return self.image
