"""A module for working with catalog channel content."""

from typing import Any


class CatalogChannel:
    """
    A class representing a channel in the catalog.
    """

    def __init__(self, definition: dict[str, Any], catalog: Any):
        self.definition = definition
        self.catalog = catalog

    @property
    def name(self) -> str:
        """A channel name property.

        Returns:
            str: A name of a channel as defined in the catalog.
        """
        return self.definition.get("name", "") or ""

    @property
    def package_name(self) -> str:
        """
        A channel package name property.

        Returns:
            str: A name of a package for a channel.
        """
        return self.definition.get("package", "") or ""

    def __str__(self) -> str:
        """A string representation of a channel given its package and name."""
        return f"{self.package_name}/{self.name}"

    def __repr__(self) -> str:
        """A representation of a CatalogChannel object."""
        return f"CatalogChannel({self.package_name}/{self.name})"

    def print(self) -> None:
        """A method to print channel details in a human-readable format."""
        print(f"Channel: {self}")
        print(f"Package: {self.catalog.get_package(self.package_name)}")
        bundles = self.catalog.get_bundles_by_package(self.package_name)
        print("Bundles:")
        for bundle in bundles:
            print(f" - {bundle}")
