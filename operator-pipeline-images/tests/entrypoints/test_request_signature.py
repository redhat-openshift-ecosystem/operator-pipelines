import base64
import json
import pytest
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
    mock_request_id = "request123"
    request_signature.request_ids = [mock_request_id]
    request_signature.result_file = "signing_response.json"
    mock_open = mock.mock_open()
    mock_msg = {"msg": {"request_id": mock_request_id}}
    with mock.patch("builtins.open", mock_open):
        request_signature.process_message(json.dumps(mock_msg))

    mock_open.assert_called_once_with(f"{mock_request_id}-signing_response.json", "w")
    mock_exit.assert_called_once_with(0)


def test_process_message_no_match() -> None:
    request_signature.request_ids = ["request123"]
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
    args.output = "output.json"
    args.requester = "test-requester"
    args.sig_key_name = "testkey"
    args.sig_key_id = "123"

    mock_gen_claim.return_value = "test-claim"
    mock_gen_image_name.return_value = "test/image-name"

    request_msg = request_signature.gen_request_msg(
        args,
        digest="test-digest",
        reference="test-reference",
        request_id="request_id123",
    )
    assert request_msg == {
        "claim_file": "test-claim",
        "docker_reference": "test-reference",
        "image_name": "test/image-name",
        "manifest_digest": "test-digest",
        "request_id": "request_id123",
        "requested_by": args.requester,
        "sig_keyname": args.sig_key_name,
        "sig_key_id": args.sig_key_id,
    }


def test_request_signature_uneven_manifest_and_reference() -> None:
    args = MagicMock
    args.manifest_digest = "a,b,c"
    args.reference = "d,e"
    with pytest.raises(SystemExit) as e:
        request_signature.request_signature(args)
        assert e.exception.code == 1


@patch("json.load")
@patch("time.sleep")
@patch("os.path.exists")
@patch("operatorcert.entrypoints.request_signature.gen_request_msg")
@patch("operatorcert.entrypoints.request_signature.start_umb_client")
def test_request_signature_single_request_no_retry(
    mock_start_umb: MagicMock,
    mock_request_msg: MagicMock,
    mock_path_exists: MagicMock,
    mock_sleep: MagicMock,
    mock_json_load: MagicMock,
) -> None:
    mock_umb = MagicMock()
    mock_start_umb.return_value = mock_umb
    mock_path_exists.return_value = True
    mock_request_msg.return_value = {"request_id": "request_id123"}
    mock_json_load.return_value = {
        "request_id": "request_id123",
        "signing_status": "success",
    }
    args = MagicMock()
    args.manifest_digest = "test-manifest"
    args.reference = "test-reference"
    args.output = "output.json"
    args.umb_client_name = "test-client"
    args.umb_url = "test.umb"
    args.umb_listen_topic = "Virtualtopic.test.listen"
    args.umb_publish_topic = "Virtualtopic.test.publish"

    mock_open = mock.mock_open()
    with mock.patch("builtins.open", mock_open):
        request_signature.request_signature(args)
    mock_umb.connect_and_subscribe.assert_called_once_with(args.umb_listen_topic)
    mock_umb.send.assert_called_once_with(
        args.umb_publish_topic, json.dumps({"request_id": "request_id123"})
    )
    mock_sleep.assert_called_once()
    mock_umb.unsubscribe.assert_called_once_with(args.umb_listen_topic)
    mock_umb.stop.assert_called_once()


@patch("json.load")
@patch("time.sleep")
@patch("os.path.exists")
@patch("operatorcert.entrypoints.request_signature.gen_request_msg")
@patch("operatorcert.entrypoints.request_signature.start_umb_client")
def test_request_signature_multi_request_no_retry(
    mock_start_umb: MagicMock,
    mock_request_msg: MagicMock,
    mock_path_exists: MagicMock,
    mock_sleep: MagicMock,
    mock_json_load: MagicMock,
) -> None:
    mock_umb = MagicMock()
    mock_start_umb.return_value = mock_umb
    mock_path_exists.return_value = True
    mock_request_msg.return_value = {"request_id": "request_id123"}
    mock_json_load.return_value = {
        "request_id": "request_id123",
        "signing_status": "success",
    }
    args = MagicMock()
    args.manifest_digest = "test-manifest1,test-manifest2,test-manifest3"
    args.reference = "test-reference1,test-reference2,test-reference3"
    args.output = "output.json"
    args.umb_client_name = "test-client"
    args.umb_url = "test.umb"
    args.umb_listen_topic = "Virtualtopic.test.listen"
    args.umb_publish_topic = "Virtualtopic.test.publish"

    mock_open = mock.mock_open()
    with mock.patch("builtins.open", mock_open):
        request_signature.request_signature(args)
    mock_umb.connect_and_subscribe.assert_called_once_with(args.umb_listen_topic)
    mock_umb.send.assert_called_with(
        args.umb_publish_topic, json.dumps({"request_id": "request_id123"})
    )
    assert mock_umb.send.call_count == 3
    mock_sleep.assert_called_once()
    mock_umb.unsubscribe.assert_called_once_with(args.umb_listen_topic)
    mock_umb.stop.assert_called_once()


@patch("json.load")
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
    mock_json_load: MagicMock,
) -> None:
    # check case where result files are not found
    mock_umb = MagicMock()
    mock_start_umb.return_value = mock_umb
    mock_path_exists.return_value = False
    mock_request_msg.return_value = {"request_id": "request_id123"}
    mock_json_load.return_value = {
        "request_id": "request_id123",
        "signing_status": "success",
    }
    args = MagicMock()
    args.manifest_digest = "test-manifest"
    args.reference = "test-reference"
    args.output = "output.json"
    args.umb_client_name = "test-client"
    args.umb_url = "test.umb"
    args.umb_listen_topic = "Virtualtopic.test.listen"
    args.umb_publish_topic = "Virtualtopic.test.publish"

    request_signature.TIMEOUT_COUNT = 1
    request_signature.WAIT_INTERVAL_SEC = 0.1

    mock_open = mock.mock_open()
    with mock.patch("builtins.open", mock_open):
        request_signature.request_signature(args)
    mock_umb.connect_and_subscribe.assert_called_once_with(args.umb_listen_topic)
    mock_umb.send.assert_called_with(
        args.umb_publish_topic, json.dumps({"request_id": "request_id123"})
    )
    # 1 initial send + 3 retries
    assert mock_umb.send.call_count == 4
    # 1 sleep per try
    assert mock_sleep.call_count == 4
    mock_umb.unsubscribe.assert_called_once_with(args.umb_listen_topic)
    mock_umb.stop.assert_called_once()
    mock_exit.assert_called_once_with(1)

    # check case where result files are found but signing failed or is unknown

    for signing_status in ["failure", "unknown"]:
        mock_umb.reset_mock()
        mock_sleep.reset_mock()
        mock_exit.reset_mock()

        mock_path_exists.return_value = True
        mock_json_load.return_value = {
            "request_id": "request_id123",
            "signing_status": signing_status,
        }

        with mock.patch("builtins.open", mock_open):
            request_signature.request_signature(args)

        mock_umb.connect_and_subscribe.assert_called_once_with(args.umb_listen_topic)
        mock_umb.send.assert_called_with(
            args.umb_publish_topic, json.dumps({"request_id": "request_id123"})
        )
        # 1 initial send + 3 retries
        assert mock_umb.send.call_count == 4
        # 1 sleep per try
        assert mock_sleep.call_count == 4
        mock_umb.unsubscribe.assert_called_once_with(args.umb_listen_topic)
        mock_umb.stop.assert_called_once()
        mock_exit.assert_called_once_with(1)
