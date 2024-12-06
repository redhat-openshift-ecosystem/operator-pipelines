"""A common test suite for file based catalog"""

from collections.abc import Iterator

from operator_repo import OperatorCatalog, OperatorCatalogList
from operator_repo.checks import CheckResult, Fail


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

    allowed_registries = None
    for catalog in operator_catalogs:
        if not isinstance(allowed_registries, list):
            # get config only once
            allowed_registries = catalog.repo.config.get(
                "allowed_bundle_registries", []
            )
        if not allowed_registries:
            # nothing to check if no registry restriction is defined
            break
        bundle_images = _get_bundle_registries_from_catalog(catalog)
        invalid_images = _filter_invalid_images(bundle_images, allowed_registries)
        if invalid_images:
            yield Fail(
                f"Invalid bundle image(s) found in {str(catalog)}: "
                f"{', '.join(invalid_images)}"
            )
