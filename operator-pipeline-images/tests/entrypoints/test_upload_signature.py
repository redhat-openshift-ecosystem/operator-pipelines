import pytest
from requests.exceptions import HTTPError
from requests.models import Response
from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import upload_signature


@patch("json.load")
@patch("operatorcert.entrypoints.upload_signature.setup_argparser")
@patch("operatorcert.entrypoints.upload_signature.upload_signature")
def test_main(
    mock_upload_signature: MagicMock,
    mock_arg_parser: MagicMock,
    mock_json_load: MagicMock,
) -> None:
    mock_arg_parser.parse_args = MagicMock
    mock_arg_parser.parse_args.pyxis_url = "https://test-pyxis.fake.url"
    mock_json_load.return_value = [{"request_id": "request_id123"}]
    upload_signature.main()
    mock_upload_signature.assert_called_once_with(
        {"request_id": "request_id123"}, "https://test-pyxis.fake.url"
    )


def test_parse_repository_name():
    test_data = {
        "registry.com/repo": "repo",
        "registry.com/namespace/repo": "namespace/repo",
        "registry.com/namespace/repo2:latest": "namespace/repo2",
        "registry.com/namespace/repo3@sha256:123": "namespace/repo3",
        "docker://registry.com/namespace/repo4@sha256:123": "namespace/repo4",
    }
    for pull_spec, expected_repo in test_data.items():
        result = upload_signature.parse_repository_name(pull_spec)
        assert result == expected_repo


@patch("operatorcert.entrypoints.upload_signature.parse_repository_name")
@patch("operatorcert.entrypoints.upload_signature.pyxis.post")
def test_upload_signature(mock_post: MagicMock, mock_repo_name: MagicMock) -> None:
    data = {
        "manifest_digest": "sha256:123456",
        "docker_reference": "registry.redhat.io/redhat/community-operator-index:v4.9",
        "sig_key_id": "testkeyid",
        "signed_claim": "dGVzdHNpZ25hdHVyZWRhdGEK",
    }
    upload_signature.upload_signature(data, "https://test-pyxis.fake.url")
    mock_post.assert_called_once_with(
        "https://test-pyxis.fake.url/v1/signatures",
        {
            "manifest_digest": data["manifest_digest"],
            "reference": data["docker_reference"],
            "repository": mock_repo_name.return_value,
            "sig_key_id": data["sig_key_id"],
            "signature_data": data["signed_claim"],
        },
    )


@patch("operatorcert.entrypoints.upload_signature.pyxis.post")
def test_upload_signature_http_errors(mock_post: MagicMock) -> None:
    data = {
        "manifest_digest": "sha256:123456",
        "docker_reference": "registry.redhat.io/redhat/community-operator-index:v4.9",
        "sig_key_id": "testkeyid",
        "signed_claim": "dGVzdHNpZ25hdHVyZWRhdGEK",
    }
    pyxis_url = "https://test-pyxis.fake.url"

    fake_rsp = Response()
    fake_rsp.status_code = 409
    fake_err = HTTPError(response=fake_rsp)
    mock_post.side_effect = fake_err
    upload_signature.upload_signature(data, pyxis_url)

    fake_rsp.status_code = 404
    fake_err = HTTPError(response=fake_rsp)
    mock_post.side_effect = fake_err
    with pytest.raises(HTTPError):
        upload_signature.upload_signature(data, pyxis_url)
