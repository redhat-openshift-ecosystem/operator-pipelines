from operatorcert.catalog.catalog import Catalog, CatalogImage
from unittest.mock import MagicMock, patch


def test_catalog(catalog: Catalog) -> None:
    assert catalog
    assert catalog.content_types

    expected_content_types = set(["olm.package", "olm.channel", "olm.bundle"])
    assert set(catalog.content_types.keys()) == expected_content_types

    packages = catalog.get_all_packages()
    assert len(packages) == 5

    channels = catalog.get_all_channels()
    assert len(channels) == 9

    bundles = catalog.get_all_bundles()
    assert len(bundles) == 5

    assert catalog.get_package("unknown") is None
    assert catalog.get_bundle("unknown") is None


def test_CatalogImage() -> None:
    image = "quay.io/operatorhubio/catalog:latest"
    catalog_image = CatalogImage(image)
    assert catalog_image.image == image

    assert str(catalog_image) == image


@patch("operatorcert.catalog.catalog.run_command")
def test_CatalogImage_catalog_content(mock_run_command: MagicMock) -> None:
    mock_run_command.return_value.stdout = b'{"schema": "olm.package", "name": "foo"}'

    image = "quay.io/operatorhubio/catalog:latest"
    catalog_image = CatalogImage(image)

    assert catalog_image.catalog_content
