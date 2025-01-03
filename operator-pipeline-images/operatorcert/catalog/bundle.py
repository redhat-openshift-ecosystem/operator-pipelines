"""Module representing a bundle in the catalog."""

from typing import Any


class CatalogBundle:
    """
    A class representing a bundle in the catalog.
    """

    def __init__(self, definition: dict[str, Any], catalog: Any):
        self.definition = definition
        self.catalog = catalog

    @property
    def name(self) -> str:
        """
        A bundle name property.

        Returns:
            str: A bundle name.
        """
        return self.definition.get("name", "") or ""

    @property
    def package_name(self) -> str:
        """
        A package name property.

        Returns:
            str: A name of a bundle package.
        """
        return self.definition.get("package", "") or ""

    @property
    def image(self) -> str:
        """
        A bundle image property.

        Returns:
            str: A bundle image pull spec as defined in the catalog.
        """
        return self.definition.get("image", "") or ""

    def __str__(self) -> str:
        """
        String representation of a bundle.

        Returns:
            str: A name of a bundle.
        """
        return self.name

    def __repr__(self) -> str:
        """
        A representation of a bundle.

        Returns:
            str: A representation of a bundle class.
        """
        return f"CatalogBundle({self.name})"

    def get_channels(self) -> list[Any]:
        """
        Get all channels for a bundle.

        Returns:
            list: A list of channels where the bundle is available.
        """
        channels = []
        for channel in self.catalog.get_all_channels():
            if channel.package_name == self.package_name:
                channels.append(channel)
        return channels

    def print(self) -> None:
        """
        Print details of a bundle in a formatted way.
        """
        print(f"Bundle: {self}")
        print(f"Package: {self.catalog.get_package(self.package_name)}")
        print(f"Image: {self.image}")

        print("Channels:")
        for channel in self.get_channels():
            print(f" - {channel}")
