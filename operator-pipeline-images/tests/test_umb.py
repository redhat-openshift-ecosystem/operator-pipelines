from operatorcert.umb import UmbClient, start_umb_client
from typing import Any
from unittest.mock import MagicMock, patch


def create_test_umb_client() -> UmbClient:
    return UmbClient(
        hostnames=[("test.umb.redhat.com", 61612)],
        cert_file="/tmp/test.crt",
        key_file="/tmp/test.key",
        handler=MagicMock(),
        umb_client_name="test-client",
    )


@patch("operatorcert.umb.stomp.Connection")
def test_connect_and_subscribe(mock_connection: MagicMock) -> None:
    mock_connection.return_value = MagicMock()
    mock_connect_obj = mock_connection.return_value
    mock_connect_obj.is_connected.return_value = False
    umb = create_test_umb_client()
    umb.connect_and_subscribe("VirtualTopic.eng.test.topic")
    mock_connect_obj.connect.assert_called_once_with(wait=True)
    mock_connect_obj.subscribe.assert_called_once_with(
        destination=f"/queue/Consumer.test-client.{umb.id}.VirtualTopic.eng.test.topic",
        id=umb.id,
        ack="auto",
        headers={"activemq.prefetchSize": 1},
    )


@patch("operatorcert.umb.stomp.Connection")
def test_send(mock_connection: MagicMock) -> None:
    mock_connection.return_value = MagicMock()
    mock_connect_obj = mock_connection.return_value
    mock_connect_obj.is_connected.return_value = False
    umb = create_test_umb_client()
    umb.send("VirtualTopic.eng.test.topic", '{"foo":"bar"}')
    mock_connect_obj.connect.assert_called_once_with(wait=True)
    mock_connect_obj.send.assert_called_once_with(
        body='{"foo":"bar"}', destination="/topic/VirtualTopic.eng.test.topic"
    )


@patch("operatorcert.umb.stomp.Connection")
def test_stop(mock_connection: MagicMock) -> None:
    mock_connection.return_value = MagicMock()
    umb = create_test_umb_client()
    umb.stop()
    mock_connection.return_value.disconnect.assert_called_once()


@patch("operatorcert.umb.stomp.Connection")
def test_unsubscribe(mock_connection: MagicMock) -> None:
    mock_connection.return_value = MagicMock()
    umb = create_test_umb_client()
    umb.unsubscribe("VirtualTopic.eng.test.topic")
    mock_connection.return_value.unsubscribe.assert_called_once_with(
        destination=f"/queue/Consumer.test-client.{umb.id}.VirtualTopic.eng.test.topic",
        id=umb.id,
    )


@patch("os.path.exists")
def test_start_umb_client(mock_path_exists: MagicMock, monkeypatch: Any) -> None:
    mock_path_exists.return_value = True
    mock_handler = MagicMock()
    monkeypatch.setenv("UMB_CERT_PATH", "/tmp/umb/cert")
    monkeypatch.setenv("UMB_KEY_PATH", "/tmp/umb/key")

    client = start_umb_client(["foo.bar"], "test-client", mock_handler)
    assert client.hostnames == [("foo.bar", 61612)]
    assert client.cert_file == "/tmp/umb/cert"
    assert client.key_file == "/tmp/umb/key"
    assert client.handler == mock_handler
    assert client.umb_client_name == "test-client"


@patch("sys.exit")
@patch("os.path.exists")
def test_start_umb_client_no_auth(
    mock_path_exists: MagicMock, mock_exit: MagicMock, monkeypatch: Any
) -> None:
    start_umb_client(["foo.bar"], "test-client", MagicMock())
    mock_exit.assert_called_once()

    mock_exit.reset_mock()
    monkeypatch.setenv("UMB_CERT_PATH", "/tmp/umb/cert")
    monkeypatch.setenv("UMB_KEY_PATH", "/tmp/umb/key")
    mock_path_exists.return_value = False
    start_umb_client(["foo.bar"], "test-client", MagicMock())
    mock_exit.assert_called_once()
