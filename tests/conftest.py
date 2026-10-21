import pathlib
import pytest
from operatorcert.catalog.catalog import Catalog
from operatorcert.catalog.package import CatalogPackage
from operatorcert.catalog.channel import CatalogChannel
from operatorcert.catalog.bundle import CatalogBundle
from operatorcert.static_tests.helpers import set_affected_operator_files
from typing import Iterator, Optional


@pytest.fixture(autouse=True)
def reset_affected_operator_files() -> Iterator[None]:
    """Ensure module-global affected-file state does not leak across tests."""
    set_affected_operator_files([])
    yield
    set_affected_operator_files([])


@pytest.fixture
def catalog() -> Catalog:
    data_dir = pathlib.Path(__file__).parent.resolve() / "data"
    return Catalog.from_file(str(data_dir / "test_catalog.yaml"))


@pytest.fixture
def catalog_package(catalog: Catalog) -> Optional[CatalogPackage]:
    return catalog.get_package("mariadb-operator")


@pytest.fixture
def catalog_channel(catalog: Catalog) -> CatalogChannel:
    # There is only one channel in the test catalog named "stable"
    return catalog.get_channels("stable")[0]


@pytest.fixture
def catalog_bundle(catalog: Catalog) -> Optional[CatalogBundle]:
    return catalog.get_bundle("mariadb-operator.v0.21.0")
