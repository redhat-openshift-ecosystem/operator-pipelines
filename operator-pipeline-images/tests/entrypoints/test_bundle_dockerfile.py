from unittest.mock import MagicMock, patch

from operatorcert.entrypoints.bundle_dockerfile import generate_dockerfile_content


@patch("operatorcert.entrypoints.bundle_dockerfile.setup_argparser")
@patch("operatorcert.entrypoints.bundle_dockerfile.pathlib.Path")
@patch("operatorcert.get_bundle_annotations")
def test_generate_dockerfile_content(
    mock_annotations: MagicMock, mock_path: MagicMock, mock_arg_parser: MagicMock
) -> None:
    args = MagicMock()
    args.bundle_path = "demo.yml"

    mock_annotations.return_value = {
        "operators.operatorframework.io.bundle.manifests.v1": "demo1",
        "operators.operatorframework.io.bundle.metadata.v1": "demo2",
    }
    dockerfile = generate_dockerfile_content(args)
    assert dockerfile is not None
