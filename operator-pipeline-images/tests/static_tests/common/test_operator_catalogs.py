from pathlib import Path
from typing import Any

import pytest
from operatorcert.operator_repo import OperatorCatalogList, Repo
from operatorcert.static_tests.common.operator_catalogs import (
    check_bundle_images_in_fbc,
)
from tests.utils import bundle_files, catalog_files, create_files


@pytest.mark.parametrize(
    ["config", "expected_results"],
    [
        (
            {},
            set(),
        ),
        (
            {
                "allowed_bundle_registries": ["quay.io/org-foo/", "quay.io/org-bar/"],
            },
            set(),
        ),
        (
            {
                "allowed_bundle_registries": ["quay.io/org-foo/"],
            },
            {
                "Invalid bundle image(s) found in OperatorCatalog(v4.14/fake-operator): "
                "quay.io/org-bar/registry/bundle@sha256:123. "
                "Only these registries are allowed for bundle images: "
                "quay.io/org-foo/.",
            },
        ),
    ],
    ids=[
        "Config not set",
        "All registries allowed",
        "Registry not allowed",
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
