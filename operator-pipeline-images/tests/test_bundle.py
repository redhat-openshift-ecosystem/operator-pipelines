from unittest import mock
from unittest.mock import MagicMock, patch

from operatorcert.bundle import BundleImage
from pytest import fixture


@fixture
def bundle() -> BundleImage:
    return BundleImage("quay.io/fake-bundle:v0.0.1", auth_file_path="fake_auth_file")


def test_BundleImage(bundle: BundleImage) -> None:
    assert str(bundle) == "quay.io/fake-bundle:v0.0.1"
    assert repr(bundle) == "BundleImage(quay.io/fake-bundle:v0.0.1)"


@patch("operatorcert.bundle.BundleImage._copy_and_extract_image")
@patch("operatorcert.bundle.tempfile.mkdtemp")
def test_Bundle_content_path(
    mock_tmp: MagicMock, mock_copy_extract: MagicMock, bundle: BundleImage
) -> None:
    result = bundle.content_path

    assert result == mock_tmp.return_value
    mock_copy_extract.assert_called_once()


@patch("operatorcert.bundle.utils.run_command")
def test_BundleImage_inspect_data(mock_command: MagicMock, bundle: BundleImage) -> None:
    mock_command.return_value.stdout = b"{}"
    result = bundle.inspect_data
    mock_command.assert_called_once_with(
        [
            "skopeo",
            "inspect",
            "--no-tags",
            "docker://quay.io/fake-bundle:v0.0.1",
            "--authfile",
            "fake_auth_file",
        ]
    )

    assert result == {}


@patch("operatorcert.bundle.BundleImage._extract_content")
@patch("operatorcert.bundle.BundleImage._copy_image")
def test_BundleImage__copy_and_extract_image(
    mock_copy: MagicMock, mock_extract: MagicMock, bundle: BundleImage
) -> None:
    bundle._copy_and_extract_image()

    mock_copy.assert_called_once()
    mock_extract.assert_called_once()


@patch("operatorcert.bundle.utils.run_command")
def test_BundleImage__copy_image(mock_command: MagicMock, bundle: BundleImage) -> None:
    bundle._content_path = "fake_path"
    bundle._copy_image()

    mock_command.assert_called_once_with(
        [
            "skopeo",
            "copy",
            "docker://quay.io/fake-bundle:v0.0.1",
            "dir:fake_path",
            "--authfile",
            "fake_auth_file",
        ]
    )


@patch("operatorcert.bundle.BundleImage.manifest_file")
@patch("operatorcert.bundle.utils.run_command")
def test_BundleImage__extract_content(
    mock_command: MagicMock, mock_manifest_file: MagicMock, bundle: BundleImage
) -> None:
    mock_manifest_file.get.return_value = [{"digest": "sha256:fake_digest"}]
    bundle._content_path = "fake_path"

    bundle._extract_content()

    mock_command.assert_called_once_with(
        ["tar", "-xvf", "fake_path/fake_digest"], cwd="fake_path"
    )


def test_BundleImage_labels(bundle: BundleImage) -> None:
    bundle._inspect_data = {"Labels": {"foo": "bar"}}
    result = bundle.labels

    assert result == {"foo": "bar"}


@patch("operatorcert.bundle.json.load")
def test_BundleImage_manifest_file(mock_json: MagicMock, bundle: BundleImage) -> None:

    bundle._content_path = "fake_path"
    mock_open = mock.mock_open()
    mock_json.return_value = {"foo": "bar"}

    with mock.patch("builtins.open", mock_open):
        result = bundle.manifest_file

        mock_open.assert_called_once_with("fake_path/manifest.json", encoding="utf8")
        mock_json.assert_called_once_with(mock_open.return_value)
        assert result == {"foo": "bar"}


@patch("operatorcert.bundle.json.load")
@patch("operatorcert.bundle.BundleImage.manifest_file")
@patch("operatorcert.bundle.utils.run_command")
def test_BundleImage_config(
    mock_command: MagicMock,
    mock_manifest_file: MagicMock,
    mock_json: MagicMock,
    bundle: BundleImage,
) -> None:
    mock_manifest_file.get.return_value = {"digest": "sha256:fake_digest"}
    bundle._content_path = "fake_path"

    mock_open = mock.mock_open()
    mock_json.return_value = {"foo": "bar"}

    with mock.patch("builtins.open", mock_open):
        result = bundle.config

    assert result == {"foo": "bar"}
    mock_open.assert_called_once_with("fake_path/fake_digest", encoding="utf8")


def test_BundleImage_get_bundle_file(bundle: BundleImage) -> None:
    bundle._content_path = "fake_path"

    mock_open = mock.mock_open()
    mock_open.return_value.read.return_value = "bar"
    with mock.patch("builtins.open", mock_open):
        result = bundle.get_bundle_file("fake_file")

    assert result == "bar"
    mock_open.assert_called_once_with("fake_path/fake_file", encoding="utf8")


@patch("operatorcert.bundle.BundleImage.get_bundle_file")
@patch("operatorcert.bundle.os.listdir")
def test_BundleImage_get_csv_file(
    mock_list_dir: MagicMock, mock_bundle_file: MagicMock, bundle: BundleImage
) -> None:
    bundle._content_path = "fake_path"
    mock_list_dir.return_value = ["fake_file"]

    result = bundle.get_csv_file()

    assert result is None

    mock_list_dir.return_value = ["foo.clusterserviceversion.yaml"]

    result = bundle.get_csv_file()
    assert result == mock_bundle_file.return_value

    mock_bundle_file.assert_called_once_with("manifests/foo.clusterserviceversion.yaml")


def test_BundleImage_annotations(bundle: BundleImage) -> None:
    bundle.get_bundle_file = MagicMock(return_value="foo: bar")  # type: ignore
    result = bundle.annotations

    assert result == {"foo": "bar"}
    bundle.get_bundle_file.assert_called_once_with("metadata/annotations.yaml")
