from pathlib import Path

import pytest
from operatorcert.operator_repo import Bundle, Repo
from operatorcert.operator_repo.exceptions import (
    InvalidBundleException,
    InvalidOperatorException,
)
from tests.utils import bundle_files, create_files


def test_bundle(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
    )
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.1")
    assert bundle.root == operator.root / "0.0.1"
    assert bundle.csv_operator_name == "hello"
    assert bundle.csv_operator_version == "0.0.1"
    assert (
        bundle.annotations["operators.operatorframework.io.bundle.package.v1"]
        == "hello"
    )
    assert bundle.dependencies == []
    assert bundle.release_config == None


def test_bundle_with_release_config(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
        {"operators/hello/0.0.1/release-config.yaml": {"catalogs": []}},
    )
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.1")

    assert bundle.release_config == {"catalogs": []}


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
    assert hello_bundle_1 < world_bundle_1
    assert operator_hello.bundle("0.0.1") != operator_hello
    with pytest.raises(TypeError):
        _ = operator_hello.bundle("0.0.1") < operator_hello


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
    assert operator.channels == {"beta"}
    assert operator.default_channel == "beta"


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
        bundle_files("invalid_metadata_contents", "0.0.1"),
        {
            "operators/invalid_metadata_contents/0.0.1/metadata/annotations.yaml": [],
        },
        bundle_files("empty_metadata", "0.0.1"),
        {
            "operators/empty_metadata/0.0.1/metadata/annotations.yaml": "",
        },
        {
            "operators/missing_csv/0.0.1/metadata/annotations.yaml": {
                "annotations": {}
            },
            "operators/missing_csv/0.0.1/manifests": None,
        },
        bundle_files("one_empty_bundle", "0.0.1"),
        {
            "operators/one_empty_bundle/0.0.2": None,
        },
    )
    repo = Repo(tmp_path)
    with pytest.raises(InvalidBundleException, match="has invalid .metadata.name"):
        _ = repo.operator("invalid_csv_name").bundle("0.0.1").csv_operator_name
    assert not repo.has("missing_manifests")
    with pytest.raises(InvalidBundleException, match="Not a valid bundle"):
        _ = Bundle(repo.root / "operators" / "missing_manifests" / "0.0.1")
    with pytest.raises(InvalidOperatorException, match="Not a valid operator"):
        _ = repo.operator("missing_manifests")
    assert repo.has("invalid_csv_contents")
    with pytest.raises(InvalidBundleException, match="Invalid CSV contents"):
        _ = repo.operator("invalid_csv_contents").bundle("0.0.1").csv_operator_version
    with pytest.raises(InvalidBundleException, match="Invalid .* contents"):
        _ = repo.operator("invalid_metadata_contents").bundle("0.0.1").annotations
    assert repo.operator("empty_metadata").bundle("0.0.1").annotations == {}
    assert repo.operator("empty_metadata").channels == set()
    assert repo.operator("empty_metadata").default_channel is None
    assert repo.has("missing_csv")
    with pytest.raises(InvalidBundleException, match="CSV file for .* not found"):
        _ = repo.operator("missing_csv").bundle("0.0.1").csv_operator_name
    assert list(repo.operator("one_empty_bundle")) == [
        repo.operator("one_empty_bundle").bundle("0.0.1")
    ]


def test_bundle_caching(mock_bundle: Bundle) -> None:
    assert Bundle(mock_bundle.root).operator == mock_bundle.operator
    assert Bundle(mock_bundle.root).operator is not mock_bundle.operator


def test_bundle_manifest_files(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
        {
            "operators/hello/0.0.1/manifests/sample_doc.yaml": "---",
            "operators/hello/0.0.1/manifests/sample_doc_2.yml": "---\nfoo: bar",
        },
    )
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.1")

    manifest_files = list(bundle.manifest_files())
    assert len(manifest_files) == 3
    assert sorted(manifest_files) == sorted(
        [
            bundle.root / "manifests" / "hello.clusterserviceversion.yaml",
            bundle.root / "manifests" / "sample_doc.yaml",
            bundle.root / "manifests" / "sample_doc_2.yml",
        ]
    )
    for manifest_file, content in bundle.manifest_files_content():
        assert manifest_file in manifest_files
        assert isinstance(content, dict)
        if manifest_file.name == "sample_doc.yaml":
            assert content == {}
        elif manifest_file.name == "sample_doc_2.yml":
            assert content == {"foo": "bar"}
        elif manifest_file.name == "hello.clusterserviceversion.yaml":
            assert content["metadata"]["name"] == "hello.v0.0.1"
        else:
            pytest.fail(f"Unexpected manifest file {manifest_file}")
