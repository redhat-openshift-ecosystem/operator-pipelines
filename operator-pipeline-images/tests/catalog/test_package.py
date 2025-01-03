from unittest.mock import MagicMock

import pytest
from operatorcert.catalog.package import CatalogPackage


def test_package(catalog_package: CatalogPackage) -> None:
    assert catalog_package.name == "mariadb-operator"
    assert len(catalog_package.get_channels()) == 1
    assert str(catalog_package) == "mariadb-operator"
    assert repr(catalog_package) == "CatalogPackage(mariadb-operator)"
    catalog_package.print()
