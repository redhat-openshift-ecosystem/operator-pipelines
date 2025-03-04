from pathlib import Path

import pytest
from operatorcert.operator_repo.exceptions import OperatorRepoException
from operatorcert.operator_repo.utils import load_multidoc_yaml, load_yaml, lookup_dict
from tests.operator_repo import create_files


def test_load_yaml(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        {"data/en.yml": {"hello": "world"}},
        {"data/it.yaml": {"ciao": "mondo"}},
        {"data/something.txt": {"foo": "bar"}},
    )
    assert load_yaml(tmp_path / "data/en.yaml") == {"hello": "world"}
    assert load_yaml(tmp_path / "data/en.yml") == {"hello": "world"}
    assert load_yaml(tmp_path / "data/it.yaml") == {"ciao": "mondo"}
    assert load_yaml(tmp_path / "data/it.yml") == {"ciao": "mondo"}
    assert load_yaml(tmp_path / "data/something.txt") == {"foo": "bar"}
    with pytest.raises(FileNotFoundError):
        _ = load_yaml(tmp_path / "data/something.yaml")
    with pytest.raises(FileNotFoundError):
        _ = load_yaml(tmp_path / "data/something.yml")


def test_load_yaml_invalid(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        {"data/multi-doc.yml": "---\nhello: world\n---\nfoo: bar\n"},
        {"data/invalid.yaml": "{This is not a valid\nyaml document]\n"},
    )
    with pytest.raises(OperatorRepoException, match="contains multiple yaml documents"):
        _ = load_yaml(tmp_path / "data/multi-doc.yml")
    with pytest.raises(OperatorRepoException, match="is not a valid yaml document"):
        _ = load_yaml(tmp_path / "data/invalid.yml")


def test_load_multidoc_yaml(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        {"data/all.yml": ({"hello": "world"}, {"ciao": "mondo"})},
    )
    assert load_multidoc_yaml(tmp_path / "data/all.yaml") == [
        {"hello": "world"},
        {"ciao": "mondo"},
    ]
    with pytest.raises(FileNotFoundError):
        _ = load_multidoc_yaml(tmp_path / "data/something.yaml")


def test_load_multidoc_yaml_invalid(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        {"data/invalid.yaml": "{This is not a valid\nyaml document]\n"},
    )
    with pytest.raises(OperatorRepoException, match="is not a valid yaml document"):
        _ = load_multidoc_yaml(tmp_path / "data/invalid.yml")


def test_lookup_dict() -> None:
    data = {"hello": "world", "sub1": {"sub3": "value1"}}
    assert lookup_dict(data, "hello") == "world"
    assert lookup_dict(data, "sub1.sub3") == "value1"
    assert lookup_dict(data, "sub1/sub3", separator="/") == "value1"
    assert lookup_dict(data, "sub2") is None
    assert lookup_dict(data, "sub2", default="") == ""
