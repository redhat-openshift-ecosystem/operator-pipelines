from pathlib import Path

import pytest
from operatorcert.operator_repo import Catalog, Repo
from operatorcert.operator_repo.exceptions import InvalidCatalogException
from tests.utils import bundle_files, catalog_files, create_files


def test_no_catalog(tmp_path: Path) -> None:
    create_files(tmp_path, bundle_files("fake-operator", "0.0.1"))
    repo = Repo(tmp_path)
    assert list(repo.all_catalogs()) == []


def test_invalid_catalog(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        catalog_files("v4.14", "fake-operator"),
        bundle_files("fake-operator", "0.0.1"),
    )
    repo = Repo(tmp_path)
    with pytest.raises(InvalidCatalogException):
        Catalog(repo.root / "catalogs" / "not-found")


def test_catalog_empty(tmp_path: Path) -> None:
    create_files(
        tmp_path, {"catalogs/readme.txt": "hello", "operators/readme.txt": "hello"}
    )
    repo = Repo(tmp_path)
    assert not repo.has_catalog("hello")


def test_catalog_one_operator(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        catalog_files("v4.14", "fake-operator"),
        bundle_files("fake-operator", "0.0.1"),
        {"catalogs/readme.txt": "hello"},
    )
    repo = Repo(tmp_path)
    assert list(repo.all_catalogs()) == [repo.catalog("v4.14")]
    catalog = repo.catalog("v4.14")
    assert repr(catalog) == "Catalog(v4.14)"
    assert catalog.repo == repo
    assert Catalog(catalog.root).repo == repo
    operator = catalog.operator_catalog("fake-operator")
    assert len(list(catalog)) == 1
    assert set(catalog) == {operator}
    assert not catalog.has("not-found")
    assert catalog.has("fake-operator")


def test_catalog_compare(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        catalog_files("v4.14", "fake-operator"),
        catalog_files("v4.14", "fake-operator-2"),
        catalog_files("v4.15", "fake-operator-2"),
        bundle_files("fake-operator", "0.0.1"),
    )
    repo = Repo(tmp_path)

    assert repo.catalog("v4.14") == repo.catalog("v4.14")
    assert repo.catalog("v4.14") != repo.catalog("v4.15")
    assert repo.catalog("v4.14") < repo.catalog("v4.15")
    assert repo.catalog("v4.14") != {"foo": "bar"}
    with pytest.raises(TypeError):
        repo.catalog("v4.14") < {"foo": "bar"}
