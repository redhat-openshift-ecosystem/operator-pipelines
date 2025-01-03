from operatorcert.catalog.bundle import CatalogBundle


def test_catalog_bundle(catalog_bundle: CatalogBundle) -> None:
    assert catalog_bundle.name == "mariadb-operator.v0.21.0"
    assert catalog_bundle.package_name == "mariadb-operator"
    assert (
        catalog_bundle.image
        == "quay.io/community-operator-pipeline-stage/mariadb-operator@sha256:c7f77235deb5165754c08ebd9873c6d6b2cbe054873203ac14910720ab254846"
    )

    assert str(catalog_bundle) == "mariadb-operator.v0.21.0"
    assert repr(catalog_bundle) == "CatalogBundle(mariadb-operator.v0.21.0)"
    assert len(catalog_bundle.get_channels()) == 1
    catalog_bundle.print()
