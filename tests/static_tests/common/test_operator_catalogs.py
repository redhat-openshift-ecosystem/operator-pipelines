from pathlib import Path
from typing import Any

import pytest
from operatorcert.operator_repo import OperatorCatalogList, Repo
from operatorcert.static_tests.common.operator_catalogs import (
    check_bundle_images_in_fbc,
    check_olm_bundle_object_in_fbc,
)
from tests.utils import bundle_files, catalog_files, create_files


@pytest.mark.parametrize(
    ["config", "expected_results"],
    [
        pytest.param(
            {},
            set(),
            id="Config not set",
        ),
        pytest.param(
            {
                "allowed_bundle_registries": ["quay.io/org-foo/", "quay.io/org-bar/"],
            },
            set(),
            id="All registries allowed",
        ),
        pytest.param(
            {
                "allowed_bundle_registries": ["quay.io/org-foo/"],
            },
            {
                "Invalid bundle image(s) found in OperatorCatalog(v4.14/fake-operator): "
                "quay.io/org-bar/registry/bundle@sha256:123. "
                "Only these registries are allowed for bundle images: "
                "quay.io/org-foo/.",
            },
            id="Registry not allowed",
        ),
    ],
)
def test_check_bundle_images_in_fbc(
    tmp_path: Path,
    config: dict[str, Any],
    expected_results: set[str],
) -> None:
    catalog_content = (
        {
            "schema": "olm.bundle",
            "image": "quay.io/org-foo/registry/bundle@sha256:123",
        },
        {
            "schema": "olm.bundle",
            "image": "quay.io/org-bar/registry/bundle@sha256:123",
        },
    )
    create_files(
        tmp_path,
        catalog_files("v4.14", "fake-operator", content=catalog_content),
        bundle_files("fake-operator", "0.0.1"),
        {"config.yaml": config},
    )
    repo = Repo(tmp_path)
    catalog = repo.catalog("v4.14")
    operator_catalog = catalog.operator_catalog("fake-operator")
    catalogs = OperatorCatalogList([operator_catalog])
    assert {x.reason for x in check_bundle_images_in_fbc(catalogs)} == expected_results


@pytest.mark.parametrize(
    ["catalog_name", "catalog_content", "expected_results"],
    [
        pytest.param(
            "unknown-catalog",
            {
                "schema": "olm.bundle",
                "properties": [{"type": "olm.bundle.object"}],
            },
            set(),
            id="Uknown version of catalog",
        ),
        pytest.param(
            "v4.16",
            {
                "schema": "olm.bundle",
                "properties": [{"type": "olm.bundle.object"}],
            },
            set(),
            id="4.16 valid catalog",
        ),
        pytest.param(
            "v4.17",
            {
                "schema": "olm.bundle",
                "properties": [{"type": "olm.bundle.object"}],
            },
            {
                "Bundle object found in OperatorCatalog(v4.17/fake-operator) catalog uses "
                "'olm.bundle.object'. This is not allowed for catalogs with version `>= "
                "4.17`. Render catalog again with latest "
                "[Makefile](https://redhat-openshift-ecosystem.github.io/operator-pipelines/users/fbc_workflow/#generate-catalogs-using-templates) "
                "using `make catalogs`. Bundle object is not supported in FBC.",
            },
            id="4.17 invalid catalog",
        ),
        pytest.param(
            "v4.17",
            {
                "schema": "olm.bundle",
                "properties": [{"type": "olm.csv.metadata"}],
            },
            set(),
            id="4.17 valid catalog",
        ),
    ],
)
def test_check_olm_bundle_object_in_fbc(
    tmp_path: Path,
    catalog_name: str,
    catalog_content: Any,
    expected_results: set[str],
) -> None:

    create_files(
        tmp_path,
        catalog_files(catalog_name, "fake-operator", content=catalog_content),
        bundle_files("fake-operator", "0.0.1"),
    )
    repo = Repo(tmp_path)
    catalog = repo.catalog(catalog_name)
    operator_catalog = catalog.operator_catalog("fake-operator")
    catalogs = OperatorCatalogList([operator_catalog])
    assert {
        x.reason for x in check_olm_bundle_object_in_fbc(catalogs)
    } == expected_results
