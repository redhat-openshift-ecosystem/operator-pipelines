"""A common test suite for file based catalog"""

from collections.abc import Iterator

from operatorcert.operator_repo import OperatorCatalog, OperatorCatalogList
from operatorcert.operator_repo.checks import CheckResult, Fail
from operatorcert.utils import is_catalog_v4_17_plus


def _get_bundle_registries_from_catalog(catalog: OperatorCatalog) -> list[str]:
    """Get bundle images from catalog"""
    catalog_content = catalog.catalog_content
    bundle_images = []
    for item in catalog_content:
        if isinstance(item, dict):
            if item.get("schema") == "olm.bundle":
                if image := item.get("image"):
                    bundle_images.append(image)

    return bundle_images


def _filter_invalid_images(
    bundle_images: list[str], allowed_registries: list[str]
) -> list[str]:
    """Filter out invalid images"""
    invalid_images = []
    for image in bundle_images:
        if not any(image.startswith(registry) for registry in allowed_registries):
            invalid_images.append(image)

    return invalid_images


def check_bundle_images_in_fbc(
    operator_catalogs: OperatorCatalogList,
) -> Iterator[CheckResult]:
    """Validate if bundle image reference in fbc is in allowed registry"""

    allowed_registries = (
        operator_catalogs[0].repo.config.get("allowed_bundle_registries", [])
        if operator_catalogs
        else []
    )
    if not allowed_registries:
        return

    for catalog in operator_catalogs:
        bundle_images = _get_bundle_registries_from_catalog(catalog)
        invalid_images = _filter_invalid_images(bundle_images, allowed_registries)
        if invalid_images:
            yield Fail(
                f"Invalid bundle image(s) found in {str(catalog)}: "
                f"{', '.join(invalid_images)}. "
                "Only these registries are allowed for bundle images: "
                f"{', '.join(allowed_registries)}."
            )


def check_olm_bundle_object_in_fbc(
    operator_catalogs: OperatorCatalogList,
) -> Iterator[CheckResult]:
    """
    Check if a bundle object in the catalog uses 'olm.bundle.object' type.
    This is not allowed for catalogs with version >= 4.17.
    For such catalogs, the bundle object should be rendered again
    with the "--migrate-level bundle-object-to-csv-metadata"

    Args:
        operator_catalogs (OperatorCatalogList): A list of operator catalogs
        to check for bundle object type.

    Yields:
        Iterator[CheckResult]: An iterator with Fail results if any
        bundle object is found in the catalog.
    """

    for operator_catalog in operator_catalogs:
        if not is_catalog_v4_17_plus(operator_catalog.catalog.catalog_name):
            # Skip the check for catalogs with version < 4.17
            continue
        bundles = operator_catalog.get_catalog_bundles()
        for bundle in bundles:
            properties = bundle.get("properties", [])
            result = [
                True for prop in properties if prop.get("type") == "olm.bundle.object"
            ]
            if any(result):
                yield Fail(
                    f"Bundle object found in {operator_catalog} catalog uses 'olm.bundle.object'. "
                    "This is not allowed for catalogs with version `>= 4.17`. "
                    "Render catalog again with latest "
                    "[Makefile](https://redhat-openshift-ecosystem.github.io/operator-pipelines/"
                    "users/fbc_workflow/#generate-catalogs-using-templates) using `make catalogs`. "
                    "Bundle object is not supported in FBC."
                )
            break
