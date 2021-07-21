from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from operatorcert import utils


@pytest.fixture
def bundle(tmp_path: Path) -> None:
    tmp_path.joinpath("metadata").mkdir()
    annotations_path = tmp_path.joinpath("metadata", "annotations.yml")

    with annotations_path.open("w") as fh:
        content = {
            "annotations": {
                "operators.operatorframework.io.bundle.package.v1": "foo-operator",
                "com.redhat.openshift.versions": "4.6-4.8",
            }
        }
        yaml.safe_dump(content, fh)

    tmp_path.joinpath("manifests").mkdir()
    csv_path = tmp_path.joinpath("manifests", "foo-operator.clusterserviceversion.yml")

    with csv_path.open("w") as fh:
        content = {
            "metadata": {
                "annotations": {
                    "olm.properties": '[{"type": "olm.maxOpenShiftVersion", "value": "4.7"}]'
                },
            }
        }
        yaml.safe_dump(content, fh)

    return tmp_path


def test_find_file(tmp_path: Path) -> None:
    tmp_path.joinpath("foo", "bar").mkdir(parents=True)
    tmp_path.joinpath("foo", "baz.txt").touch()
    tmp_path.joinpath("foo", "bar", "baz.txt").touch()
    result = utils.find_file(
        tmp_path,
        [
            ("foo", "not-found.txt"),
            ("foo", "bar", "baz.txt"),
            ("foo", "baz.txt"),
        ],
    )
    assert str(result.relative_to(tmp_path)) == "foo/bar/baz.txt"

    result = utils.find_file(
        tmp_path,
        [
            ("foo", "not-found.txt"),
        ],
    )
    assert result is None


def test_get_bundle_annotations(bundle: Path) -> None:
    assert utils.get_bundle_annotations(bundle) == {
        "operators.operatorframework.io.bundle.package.v1": "foo-operator",
        "com.redhat.openshift.versions": "4.6-4.8",
    }
    bundle.joinpath("metadata", "annotations.yml").unlink()
    with pytest.raises(RuntimeError):
        utils.get_bundle_annotations(bundle)


def test_get_csv_annotations(bundle: Path) -> None:
    assert utils.get_csv_annotations(bundle, "foo-operator") == {
        "olm.properties": '[{"type": "olm.maxOpenShiftVersion", "value": "4.7"}]'
    }
    bundle.joinpath("manifests", "foo-operator.clusterserviceversion.yml").unlink()
    with pytest.raises(RuntimeError):
        utils.get_csv_annotations(bundle, "foo-operator")


@patch("requests.get")
def test_get_supported_indices(mock_get: MagicMock) -> None:
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = {"data": ["foo", "bar"]}
    mock_get.return_value = mock_rsp

    result = utils.get_supported_indices(
        "https://foo.bar", "4.6-4.8", max_ocp_version="4.7"
    )
    assert result == ["foo", "bar"]


@patch("operatorcert.utils.get_supported_indices")
def test_ocp_version_info(mock_indices: MagicMock, bundle: Path) -> None:
    mock_indices.return_value = [{"ocp_version": "4.7", "path": "quay.io/foo:4.7"}]
    info = utils.ocp_version_info(bundle, "")
    assert info == {
        "versions_annotation": "4.6-4.8",
        "max_version_property": "4.7",
        "indices": mock_indices.return_value,
        "max_version_index": mock_indices.return_value[0],
    }

    mock_indices.return_value = []
    with pytest.raises(ValueError):
        utils.ocp_version_info(bundle, "")
