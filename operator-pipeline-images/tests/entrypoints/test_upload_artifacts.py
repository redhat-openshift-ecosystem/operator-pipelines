import os.path
from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import upload_artifacts


@patch("operatorcert.entrypoints.upload_artifacts.json.dump")
@patch("operatorcert.entrypoints.upload_artifacts.setup_argparser")
@patch("operatorcert.entrypoints.upload_artifacts.upload_results_and_artifacts")
def test_main(
    mock_upload: MagicMock, mock_arg_parser: MagicMock, mock_dump: MagicMock
) -> None:
    upload_artifacts.main()
    mock_upload.assert_called_once()


@patch("operatorcert.entrypoints.upload_artifacts.base64.b64encode")
@patch("operatorcert.entrypoints.upload_artifacts.pyxis.post")
def test_upload_artifact(mock_post: MagicMock, mock_b64) -> None:
    args = MagicMock()
    args.pyxis_url = "http://foo.com/"
    args.certification_hash = "hashhash"
    args.operator_package_name = "foo"
    args.operator_version = "1.0"
    args.cert_project_id = "123123"

    mock_b64.return_value = b"a"
    filename = "operator-pipeline-images/tests/data/preflight.log"
    upload_artifacts.upload_artifact(args, filename, 1)

    mock_post.assert_called_once_with(
        "http://foo.com/v1/projects/certification/id/123123/artifacts",
        {
            "content": "a",
            "certification_hash": args.certification_hash,
            "content_type": "text/plain",
            "filename": "preflight.log",
            "file_size": os.path.getsize(filename),
            "operator_package_name": args.operator_package_name,
            "version": args.operator_version,
            "org_id": 1,
        },
    )


@patch("operatorcert.entrypoints.upload_artifacts.json.load")
@patch("operatorcert.entrypoints.upload_artifacts.pyxis.post")
def test_upload_test_results(mock_post: MagicMock, mock_load: MagicMock) -> None:
    mock_load.return_value = {}

    args = MagicMock()
    args.pyxis_url = "http://foo.com/"
    args.certification_hash = "hashhash"
    args.operator_package_name = "foo"
    args.operator_version = "1.0"
    args.cert_project_id = "123123"

    upload_artifacts.upload_test_results(args, 1)

    mock_post.assert_called_once_with(
        "http://foo.com/v1/projects/certification/id/123123/test-results",
        {
            "certification_hash": args.certification_hash,
            "operator_package_name": args.operator_package_name,
            "version": args.operator_version,
            "org_id": 1,
        },
    )
