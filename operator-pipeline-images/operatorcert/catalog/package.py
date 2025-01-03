"""A module representing a package in the catalog."""

from typing import Any


class CatalogPackage:
    """
    A class representing a package in the catalog.
    """

    def __init__(self, definition: dict[str, Any], catalog: Any) -> None:
        self.definition = definition
        self.catalog = catalog

    @property
    def name(self) -> str:
        """
        A package name property.

        Returns:
            str: A name of a package.
        """
        return self.definition.get("name", "") or ""

    def __str__(self) -> str:
        """
        String representation of a package given its name.
        """
        return self.name

    def __repr__(self) -> str:
        """
        A representation of a CatalogPackage object.
        """
        return f"CatalogPackage({self.name})"

    def get_channels(self) -> list[Any]:
        """
        Get all channels for a package.

        Returns:
            list: A list of all CatalogChannel objects for a package.
        """
        channels = []
        for channel in self.catalog.get_all_channels():
            if channel.package_name == self.name:
                channels.append(channel)
        return channels

    def get_bundles(self) -> list[Any]:
        """
        Get all bundles for a package.

        Returns:
            list: A list of all CatalogBundle objects for a package.
        """
        bundles = []
        for bundle in self.catalog.get_all_bundles():
            if bundle.package_name == self.name:
                bundles.append(bundle)
        return bundles

    def print(self) -> None:
        """
        Print package details in a human-readable format.
        """
        print(f"Package: {self.name}")
        print("Channels:")
        for channel in self.get_channels():
            print(f" - {channel}")
        print("Bundles:")
        for bundle in self.get_bundles():
            print(f" - {bundle}")
