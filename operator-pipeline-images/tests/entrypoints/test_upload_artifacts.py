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
    args.pull_request_url = "http://bar.com/"

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
            "pull_request_url": args.pull_request_url,
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


@patch("os.path.isdir")
@patch("os.listdir")
@patch("os.path.isfile")
def test_get_artifacts(
    mock_isfile: MagicMock, mock_listdir: MagicMock, mock_isdir: MagicMock
) -> None:
    # if there are no artifact paths
    mock_isdir.return_value = False
    rsp = upload_artifacts.get_artifacts("test-dir")
    assert rsp == []

    # if there are artifact paths
    mock_isdir.return_value = True
    mock_isfile.return_value = True
    mock_listdir.return_value = ["test-file", "demo", "sample-file"]
    rsp = upload_artifacts.get_artifacts("test-dir")
    assert rsp == ["test-file", "demo", "sample-file"]


@patch("operatorcert.entrypoints.upload_artifacts.upload_artifact")
@patch("operatorcert.entrypoints.upload_artifacts.get_artifacts")
def test_upload_artifacts(
    mock_get_artifacts: MagicMock, mock_upload_artifact: MagicMock
) -> None:
    args = MagicMock()
    args.path = "test-dir"
    mock_get_artifacts.return_value = ["test-file"]
    mock_upload_artifact.return_value = {
        "_id": "some_id",
        "cert_project": "sample_project_id",
        "certification_hash": "demo_hash",
        "content": "demo_content",
        "content_type": "demo_type",
        "created_by": "test",
        "creation_date": "2021-11-23T12:12:19.823Z",
        "file_size": 0,
        "filename": "test-dir/test-file",
        "last_update_date": "2021-11-23T12:12:19.823Z",
        "last_updated_by": "test",
        "operator_package_name": "demo_package",
        "org_id": 100,
        "version": "v4.9",
    }
    rsp = upload_artifacts.upload_artifacts(args, 100)
    assert rsp == [
        {
            "_id": "some_id",
            "cert_project": "sample_project_id",
            "certification_hash": "demo_hash",
            "content": "demo_content",
            "content_type": "demo_type",
            "created_by": "test",
            "creation_date": "2021-11-23T12:12:19.823Z",
            "file_size": 0,
            "filename": "test-dir/test-file",
            "last_update_date": "2021-11-23T12:12:19.823Z",
            "last_updated_by": "test",
            "operator_package_name": "demo_package",
            "org_id": 100,
            "version": "v4.9",
        }
    ]


@patch("operatorcert.entrypoints.upload_artifacts.upload_artifact")
@patch("operatorcert.entrypoints.upload_artifacts.upload_artifacts")
@patch("operatorcert.entrypoints.upload_artifacts.upload_test_results")
@patch("operatorcert.pyxis.is_internal")
@patch("operatorcert.pyxis.get_project")
def test_upload_results_and_artifacts(
    mock_get: MagicMock,
    mock_internal: MagicMock,
    mock_test_result: MagicMock,
    mock_artifacts: MagicMock,
    mock_artifact: MagicMock,
) -> None:
    args = MagicMock()
    args.pyxis_url = "https://catalog.redhat.com/api/containers/"
    args.cert_project_id = "some_project_id"
    args.path = "test-dir/test-file"

    mock_internal.return_value = True
    mock_get.return_value = {"_id": "some_id", "org_id": 100}

    # PREFLIGHT-LOGS OR PIPELINE-LOGS TYPE
    args.type = "preflight-logs"
    upload_artifacts.upload_results_and_artifacts(args)
    mock_artifact.assert_called_once()

    # PREFLIGHT-ARTIFACTS TYPE
    args.type = "preflight-artifacts"
    upload_artifacts.upload_results_and_artifacts(args)
    mock_artifacts.assert_called_once()

    # PREFLIGHT-RESULTS TYPE
    args.type = "preflight-results"
    upload_artifacts.upload_results_and_artifacts(args)
    mock_test_result.assert_called_once()
