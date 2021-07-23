from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict

import pytest
import yaml

import operatorcert

Bundle = Dict[str, Path]


@pytest.fixture
def bundle(tmp_path: Path) -> Bundle:
    tmp_path.joinpath("metadata").mkdir()
    annotations_path = tmp_path.joinpath("metadata", "annotations.yml")

    annotations = {
        "annotations": {
            "operators.operatorframework.io.bundle.package.v1": "foo-operator",
            "com.redhat.openshift.versions": "4.6-4.8",
        }
    }
    with annotations_path.open("w") as fh:
        yaml.safe_dump(annotations, fh)

    tmp_path.joinpath("manifests").mkdir()
    csv_path = tmp_path.joinpath("manifests", "foo-operator.clusterserviceversion.yml")

    csv = {
        "metadata": {
            "annotations": {
                "olm.properties": '[{"type": "olm.maxOpenShiftVersion", "value": "4.7"}]'
            },
        }
    }
    with csv_path.open("w") as fh:
        yaml.safe_dump(csv, fh)

    return {
        "root": tmp_path,
        "annotations": annotations_path,
        "csv": csv_path,
    }


def test_get_bundle_annotations(bundle: Bundle) -> None:
    bundle_root = bundle["root"]
    assert operatorcert.get_bundle_annotations(bundle_root) == {
        "operators.operatorframework.io.bundle.package.v1": "foo-operator",
        "com.redhat.openshift.versions": "4.6-4.8",
    }
    bundle["annotations"].unlink()
    with pytest.raises(RuntimeError):
        operatorcert.get_bundle_annotations(bundle_root)


def test_get_csv_annotations(bundle: Bundle) -> None:
    bundle_root = bundle["root"]
    assert operatorcert.get_csv_annotations(bundle_root, "foo-operator") == {
        "olm.properties": '[{"type": "olm.maxOpenShiftVersion", "value": "4.7"}]'
    }
    bundle["csv"].unlink()
    with pytest.raises(RuntimeError):
        operatorcert.get_csv_annotations(bundle_root, "foo-operator")


@patch("requests.get")
def test_get_supported_indices(mock_get: MagicMock) -> None:
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = {"data": ["foo", "bar"]}
    mock_get.return_value = mock_rsp

    result = operatorcert.get_supported_indices(
        "https://foo.bar", "4.6-4.8", max_ocp_version="4.7"
    )
    assert result == ["foo", "bar"]


@patch("operatorcert.get_supported_indices")
def test_ocp_version_info(mock_indices: MagicMock, bundle: Bundle) -> None:
    bundle_root = bundle["root"]
    mock_indices.return_value = [{"ocp_version": "4.7", "path": "quay.io/foo:4.7"}]
    info = operatorcert.ocp_version_info(bundle_root, "")
    assert info == {
        "versions_annotation": "4.6-4.8",
        "max_version_property": "4.7",
        "indices": mock_indices.return_value,
        "max_version_index": mock_indices.return_value[0],
    }

    mock_indices.return_value = []
    with pytest.raises(ValueError):
        operatorcert.ocp_version_info(bundle_root, "")

    annotations = {
        "annotations": {
            "operators.operatorframework.io.bundle.package.v1": "foo-operator",
        }
    }
    with bundle["annotations"].open("w") as fh:
        yaml.safe_dump(annotations, fh)

    with pytest.raises(ValueError):
        operatorcert.ocp_version_info(bundle_root, "")

    annotations["annotations"] = {"com.redhat.openshift.versions": "4.6-4.8"}
    with bundle["annotations"].open("w") as fh:
        yaml.safe_dump(annotations, fh)

    with pytest.raises(ValueError):
        operatorcert.ocp_version_info(bundle_root, "")
