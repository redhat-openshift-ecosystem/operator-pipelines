import pytest
from requests.exceptions import HTTPError
from requests.models import Response
from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import upload_signature


@patch("operatorcert.entrypoints.upload_signature.setup_argparser")
@patch("operatorcert.entrypoints.upload_signature.upload_signature")
def test_main(
    mock_upload_signature: MagicMock,
    mock_arg_parser: MagicMock,
) -> None:
    upload_signature.main()
    mock_upload_signature.assert_called_once()


@patch("operatorcert.entrypoints.upload_signature.pyxis.post")
def test_upload_signature(mock_post: MagicMock) -> None:
    args = MagicMock()
    args.pyxis_url = "https://test-pyxis.fake.url"
    args.manifest_digest = "sha256:123456"
    args.reference = "registry.redhat.io/redhat/community-operator-index:v4.9"
    args.repository = "redhat/community-operator-index"
    args.sig_key_id = "testkeyid"
    args.signature_data = "dGVzdHNpZ25hdHVyZWRhdGEK"

    upload_signature.upload_signature(args)
    mock_post.assert_called_once_with(
        "https://test-pyxis.fake.url/v1/signatures",
        {
            "manifest_digest": args.manifest_digest,
            "reference": args.reference,
            "repository": args.repository,
            "sig_key_id": args.sig_key_id,
            "signature_data": args.signature_data,
        },
    )


@patch("operatorcert.entrypoints.upload_signature.pyxis.post")
def test_upload_signature_http_errors(mock_post: MagicMock) -> None:
    args = MagicMock()
    args.pyxis_url = "https://test-pyxis.fake.url"
    args.manifest_digest = "sha256:123456"
    args.reference = "registry.redhat.io/redhat/community-operator-index:v4.9"
    args.repository = "redhat/community-operator-index"
    args.sig_key_id = "testkeyid"
    args.signature_data = "dGVzdHNpZ25hdHVyZWRhdGEK"

    fake_rsp = Response()
    fake_rsp.status_code = 409
    fake_err = HTTPError(response=fake_rsp)
    mock_post.side_effect = fake_err
    upload_signature.upload_signature(args)

    fake_rsp.status_code = 404
    fake_err = HTTPError(response=fake_rsp)
    mock_post.side_effect = fake_err
    with pytest.raises(HTTPError):
        upload_signature.upload_signature(args)
