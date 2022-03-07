import base64
import json
from unittest import mock
from unittest.mock import MagicMock, patch

from operatorcert.umb import UmbClient
from operatorcert.entrypoints import request_signature


def create_test_umb_client() -> UmbClient:
    return UmbClient(
        hostnames=[("test.umb.redhat.com", 61612)],
        cert_file="/tmp/test.crt",
        key_file="/tmp/test.key",
        handler=MagicMock(),
        umb_client_name="test-client",
    )


@patch("sys.exit")
def test_process_message_match(mock_exit: MagicMock) -> None:
    test_umb = create_test_umb_client()
    request_signature.umb = test_umb
    request_signature.result_file = "signing_response.json"
    mock_open = mock.mock_open()
    mock_msg = {"msg": {"request_id": test_umb.id}}
    with mock.patch("builtins.open", mock_open):
        request_signature.process_message(json.dumps(mock_msg))

    mock_open.assert_called_once_with("signing_response.json", "w")
    mock_exit.assert_called_once_with(0)


def test_process_message_no_match() -> None:
    test_umb = create_test_umb_client()
    request_signature.umb = test_umb
    mock_open = mock.mock_open()
    mock_msg = {"msg": {"request_id": "no-match"}}
    with mock.patch("builtins.open", mock_open):
        request_signature.process_message(json.dumps(mock_msg))

    mock_open.assert_not_called()


def test_gen_sig_claim_file() -> None:
    claim = request_signature.gen_sig_claim_file(
        reference="test-reference",
        digest="test-digest",
        requested_by="test-requester",
    )
    expected = base64.b64encode(
        json.dumps(
            {
                "critical": {
                    "image": {"docker-manifest-digest": "test-digest"},
                    "type": "atomic container signature",
                    "identity": {"docker-reference": "test-reference"},
                },
                "optional": {"creator": "test-requester"},
            }
        ).encode("utf-8")
    )
    assert claim.encode("utf-8") == expected


def test_gen_image_name() -> None:
    image_name = request_signature.gen_image_name(
        "registry.redhat.io/redhat/community-operator-index:v4.9"
    )
    assert image_name == "redhat/community-operator-index"


@patch("operatorcert.entrypoints.request_signature.gen_image_name")
@patch("operatorcert.entrypoints.request_signature.gen_sig_claim_file")
def test_gen_request_msg(
    mock_gen_claim: MagicMock, mock_gen_image_name: MagicMock
) -> None:
    args = MagicMock()
    args.manifest_digest = "test-digest"
    args.output = "output.json"
    args.reference = "test-reference"
    args.requester = "test-requester"
    args.sig_key_name = "testkey"
    args.sig_key_id = "123"

    mock_gen_claim.return_value = "test-claim"
    mock_gen_image_name.return_value = "test/image-name"

    request_msg = request_signature.gen_request_msg(args, "request_id123")
    assert request_msg == {
        "claim_file": "test-claim",
        "docker_reference": args.reference,
        "image_name": "test/image-name",
        "manifest_digest": args.manifest_digest,
        "request_id": "request_id123",
        "requested_by": args.requester,
        "sig_keyname": args.sig_key_name,
        "sig_key_id": args.sig_key_id,
    }


@patch("time.sleep")
@patch("os.path.exists")
@patch("operatorcert.entrypoints.request_signature.gen_request_msg")
@patch("operatorcert.entrypoints.request_signature.start_umb_client")
def test_request_signature_no_retry(
    mock_start_umb: MagicMock,
    mock_request_msg: MagicMock,
    mock_path_exists: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    mock_umb = MagicMock()
    mock_start_umb.return_value = mock_umb
    mock_path_exists.return_value = True
    mock_request_msg.return_value = {"request_id": "request_id123"}
    args = MagicMock()
    args.output = "output.json"
    args.umb_client_name = "test-client"
    args.umb_url = "test.umb"
    args.umb_listen_topic = "Virtualtopic.test.listen"
    args.umb_publish_topic = "Virtualtopic.test.publish"

    request_signature.request_signature(args)
    mock_umb.connect_and_subscribe.assert_called_once_with(args.umb_listen_topic)
    mock_umb.send.assert_called_once_with(
        args.umb_publish_topic, json.dumps({"request_id": "request_id123"})
    )
    mock_sleep.assert_not_called()
    mock_umb.unsubscribe.assert_called_once_with(args.umb_listen_topic)
    mock_umb.stop.assert_called_once()


@patch("sys.exit")
@patch("time.sleep")
@patch("os.path.exists")
@patch("operatorcert.entrypoints.request_signature.gen_request_msg")
@patch("operatorcert.entrypoints.request_signature.start_umb_client")
def test_request_signature_timeout(
    mock_start_umb: MagicMock,
    mock_request_msg: MagicMock,
    mock_path_exists: MagicMock,
    mock_sleep: MagicMock,
    mock_exit: MagicMock,
) -> None:
    mock_umb = MagicMock()
    mock_start_umb.return_value = mock_umb
    mock_path_exists.return_value = False
    mock_request_msg.return_value = {"request_id": "request_id123"}
    args = MagicMock()
    args.output = "output.json"
    args.umb_client_name = "test-client"
    args.umb_url = "test.umb"
    args.umb_listen_topic = "Virtualtopic.test.listen"
    args.umb_publish_topic = "Virtualtopic.test.publish"

    request_signature.TIMEOUT_COUNT = 1
    request_signature.WAIT_INTERVAL_SEC = 0.1

    request_signature.request_signature(args)
    mock_umb.connect_and_subscribe.assert_called_once_with(args.umb_listen_topic)
    mock_umb.send.assert_called_with(
        args.umb_publish_topic, json.dumps({"request_id": "request_id123"})
    )
    # 1 initial send + 3 retries
    assert mock_umb.send.call_count == 4
    # 2 sleep per try
    assert mock_sleep.call_count == 8
    mock_umb.unsubscribe.assert_called_once_with(args.umb_listen_topic)
    mock_umb.stop.assert_called_once()
    mock_exit.assert_called_once_with(1)
