from operatorcert import parsed_file


def test_AffectedBundleCollection() -> None:

    bundles = parsed_file.AffectedBundleCollection(
        added={("test_bundle", "1.0.0"), ("bundle-x", "2.9.0")},
        deleted={("bundle-y", "1.0.0"), ("bundle-x", "2.9.0")},
        modified={("bundle-z", "1.0.0"), ("bundle-x", "2.9.0")},
    )

    dict_result = bundles.to_dict()
    assert dict_result == {
        "added_bundles": ["bundle-x/2.9.0", "test_bundle/1.0.0"],
        "deleted_bundles": ["bundle-x/2.9.0", "bundle-y/1.0.0"],
        "modified_bundles": ["bundle-x/2.9.0", "bundle-z/1.0.0"],
        "added_or_modified_bundles": [
            "bundle-x/2.9.0",
            "bundle-z/1.0.0",
            "test_bundle/1.0.0",
        ],
        "affected_bundles": [
            "bundle-x/2.9.0",
            "bundle-y/1.0.0",
            "bundle-z/1.0.0",
            "test_bundle/1.0.0",
        ],
    }


def test_AffectedOperatorCollection() -> None:
    operator = parsed_file.AffectedOperatorCollection(
        added={"test_operator", "operator-x"},
        deleted={"operator-y", "operator-x"},
        modified={"operator-z", "operator-x"},
    )
    dict_result = operator.to_dict()
    assert dict_result == {
        "added_operators": ["operator-x", "test_operator"],
        "deleted_operators": ["operator-x", "operator-y"],
        "modified_operators": ["operator-x", "operator-z"],
        "added_or_modified_operators": [
            "operator-x",
            "operator-z",
            "test_operator",
        ],
        "affected_operators": [
            "operator-x",
            "operator-y",
            "operator-z",
            "test_operator",
        ],
    }


def test_AffectedCatalogOperatorCollection() -> None:
    catalog_operators = parsed_file.AffectedCatalogOperatorCollection(
        added={
            ("v4.11", "test_catalog_operator"),
            ("v4.12", "test_catalog_operator"),
            ("v4.12", "catalog_operator-x"),
        },
        deleted={("v4.12", "catalog_operator-y"), ("v4.12", "catalog_operator-x")},
        modified={("v4.12", "catalog_operator-z"), ("v4.12", "catalog_operator-x")},
    )

    dict_result = catalog_operators.to_dict()
    assert dict_result == {
        "added_catalog_operators": [
            "v4.11/test_catalog_operator",
            "v4.12/catalog_operator-x",
            "v4.12/test_catalog_operator",
        ],
        "deleted_catalog_operators": [
            "v4.12/catalog_operator-x",
            "v4.12/catalog_operator-y",
        ],
        "modified_catalog_operators": [
            "v4.12/catalog_operator-x",
            "v4.12/catalog_operator-z",
        ],
        "affected_catalog_operators": [
            "v4.11/test_catalog_operator",
            "v4.12/catalog_operator-x",
            "v4.12/catalog_operator-y",
            "v4.12/catalog_operator-z",
            "v4.12/test_catalog_operator",
        ],
        "catalogs_with_added_or_modified_operators": ["v4.11", "v4.12"],
    }


def test_AffectedCatalogCollection() -> None:
    catalogs = parsed_file.AffectedCatalogCollection(
        added={"v4.11", "v4.12", "v4.9"},
        deleted={"v4.12", "v4.22"},
        modified={"v4.12", "v4.1", "v4.33"},
    )

    dict_result = catalogs.to_dict()
    assert dict_result == {
        "added_catalogs": ["v4.9", "v4.11", "v4.12"],
        "deleted_catalogs": ["v4.12", "v4.22"],
        "modified_catalogs": ["v4.1", "v4.12", "v4.33"],
        "affected_catalogs": ["v4.1", "v4.9", "v4.11", "v4.12", "v4.22", "v4.33"],
        "added_or_modified_catalogs": ["v4.1", "v4.9", "v4.11", "v4.12", "v4.33"],
    }
