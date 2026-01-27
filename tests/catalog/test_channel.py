from operatorcert.catalog.channel import CatalogChannel


def test_catalog_channel(catalog_channel: CatalogChannel) -> None:
    assert catalog_channel.name == "stable"
    assert catalog_channel.package_name == "node-healthcheck-operator"

    assert str(catalog_channel) == "node-healthcheck-operator/stable"
    assert repr(catalog_channel) == "CatalogChannel(node-healthcheck-operator/stable)"
    catalog_channel.print()
