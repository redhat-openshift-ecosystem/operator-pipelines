from pathlib import Path
from typing import Dict, Optional, Union, Any, List

import pytest
import yaml
from operatorcert.operator_repo import (
    Bundle,
    Repo,
    InvalidBundleException,
    InvalidOperatorException,
    InvalidRepoException,
    load_yaml,
)


def merge(
    a: Dict[str, Any], b: Dict[str, Any], path: List[str] = None
) -> Dict[str, Any]:
    """Deep merge dictionary b into a and return a"""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


def create_files(path: Path, *contents: Dict[str, Any]) -> None:
    """
    Create files

    Args:
        path: Root path where the files should be created
        *contents: Dictionary containing files to be created: keys are
            treated as the relative path where the file should be created
            under the given root path. Values can be:
            string or bytes: the body of the file will contain that string
                or bytes as it is
            None: an empty directory will be created at the given path
            anything else: the file will contain a yaml structure containing
                the data
    """
    root = Path(path)
    for element in contents:
        for file_name, content in element.items():
            full_path = root / file_name
            if content is None:
                full_path.mkdir(parents=True, exist_ok=True)
            else:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, (str, bytes)):
                    full_path.write_text(content)
                else:
                    full_path.write_text(yaml.safe_dump(content))


def bundle_files(
    operator_name: str,
    bundle_version: str,
    annotations: Optional[Dict[str, Any]] = None,
    csv: Optional[Dict[str, Any]] = None,
    other_files: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a mock operator bundle on the filesystem

    Args:
        operator_name: Name of the operator
        bundle_version: Version of the bundle
        annotations: Optional dictionary containing extra annotations
            for the bundle
        csv: Optional dictionary containing extra fields for the CSV
            of the bundle
        other_files: Dictionary of extra files to inject in the bundle

    Returns:
        A dictionary representation of the files for the bundle that can
        be fed directly to create_files
    """
    bundle_path = f"operators/{operator_name}/{bundle_version}"
    base_annotations = {
        "operators.operatorframework.io.bundle.mediatype.v1": "registry+v1",
        "operators.operatorframework.io.bundle.manifests.v1": "manifests/",
        "operators.operatorframework.io.bundle.metadata.v1": "metadata/",
        "operators.operatorframework.io.bundle.package.v1": operator_name,
        "operators.operatorframework.io.bundle.channel.default.v1": "beta",
        "operators.operatorframework.io.bundle.channels.v1": "beta",
    }
    base_csv = {
        "metadata": {
            "name": f"{operator_name}.v{bundle_version}",
            "spec": {"version": bundle_version},
        }
    }
    return merge(
        {
            f"{bundle_path}/metadata/annotations.yaml": {
                "annotations": merge(base_annotations, annotations or {})
            },
            f"{bundle_path}/manifests/{operator_name}.clusterserviceversion.yaml": merge(
                base_csv, csv or {}
            ),
        },
        other_files or {},
    )


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


def test_repo_non_existent() -> None:
    with pytest.raises(InvalidRepoException, match="Not a valid operator repository"):
        _ = Repo("/non_existent")


def test_repo_empty(tmp_path: Path) -> None:
    with pytest.raises(InvalidRepoException, match="Not a valid operator repository"):
        _ = Repo(str(tmp_path))


def test_repo_no_operators(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        {
            "operators": None,
            "ci/pipeline-config.yaml": {"hello": "world"},
        },
    )
    repo = Repo(tmp_path)
    assert len(list(repo)) == 0
    assert repo.config == {"hello": "world"}
    assert repo.root() == str(tmp_path.resolve())
    assert str(tmp_path) in repr(repo)


def test_repo_one_bundle(tmp_path: Path) -> None:
    create_files(tmp_path, bundle_files("hello", "0.0.1"))
    repo = Repo(tmp_path)
    assert repo.config == {}
    assert len(list(repo)) == 1
    assert set(repo) == {repo.operator("hello")}
    assert repo.has("hello")


def test_operator_empty(tmp_path: Path) -> None:
    create_files(tmp_path, {"operators/hello/readme.txt": "hello"})
    repo = Repo(tmp_path)
    assert not repo.has("hello")


def test_operator_one_bundle(tmp_path: Path) -> None:
    create_files(tmp_path, bundle_files("hello", "0.0.1"))
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.1")
    assert len(list(operator)) == 1
    assert set(operator) == {bundle}
    assert operator.has("0.0.1")
    assert bundle.operator() == operator
    assert operator.config == {}
    assert bundle.dependencies == []
    assert operator.root() == repo.root() + "/operators/hello"
    assert "hello" in repr(operator)


def test_bundle(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
    )
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.1")
    assert bundle.root() == operator.root() + "/0.0.1"
    assert bundle.csv_operator_name == "hello"
    assert bundle.csv_operator_version == "v0.0.1"
    assert (
        bundle.annotations["operators.operatorframework.io.bundle.package.v1"]
        == "hello"
    )
    assert bundle.dependencies == []


def test_bundle_compare(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
        bundle_files("hello", "0.0.2"),
        bundle_files("world", "0.1.0"),
    )
    repo = Repo(tmp_path)
    operator_hello = repo.operator("hello")
    operator_world = repo.operator("world")
    assert operator_hello == repo.operator("hello")
    assert operator_hello != operator_world
    assert operator_hello < operator_world
    hello_bundle_1 = operator_hello.bundle("0.0.1")
    hello_bundle_2 = operator_hello.bundle("0.0.2")
    world_bundle_1 = operator_world.bundle("0.1.0")
    assert hello_bundle_1 != hello_bundle_2
    assert hello_bundle_1 < hello_bundle_2
    assert hello_bundle_1 != world_bundle_1
    with pytest.raises(ValueError):
        _ = hello_bundle_1 < world_bundle_1


def test_bundle_non_semver(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.99.0"),
        bundle_files("hello", "0.0.100.0"),
    )
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle_99 = operator.bundle("0.0.99.0")
    bundle_100 = operator.bundle("0.0.100.0")
    assert bundle_99 > bundle_100


def test_bundle_invalid(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files(
            "invalid_csv_name", "0.0.1", csv={"metadata": {"name": "rubbish"}}
        ),
        {
            "operators/missing_manifests/0.0.1/metadata/annotations.yaml": {
                "annotations": {}
            }
        },
        bundle_files("invalid_csv_contents", "0.0.1"),
        {
            "operators/invalid_csv_contents/0.0.1/manifests/invalid_csv_contents.clusterserviceversion.yaml": [],
        },
        {
            "operators/missing_csv/0.0.1/metadata/annotations.yaml": {
                "annotations": {}
            },
            "operators/missing_csv/0.0.1/manifests": None,
        },
    )
    repo = Repo(tmp_path)
    with pytest.raises(
        InvalidBundleException, match="Invalid .metadata.name in CSV for"
    ):
        _ = repo.operator("invalid_csv_name").bundle("0.0.1")
    assert not repo.has("missing_manifests")
    with pytest.raises(InvalidBundleException, match="Not a valid bundle"):
        _ = Bundle(repo.root() + "/operators/missing_manifests/0.0.1")
    with pytest.raises(InvalidOperatorException, match="Not a valid operator"):
        _ = repo.operator("missing_manifests")
    assert repo.has("invalid_csv_contents")
    with pytest.raises(InvalidBundleException, match="Invalid CSV contents"):
        _ = repo.operator("invalid_csv_contents").bundle("0.0.1")
    assert repo.has("missing_csv")
    with pytest.raises(InvalidBundleException, match="CSV file for .* not found"):
        _ = repo.operator("missing_csv").bundle("0.0.1")
