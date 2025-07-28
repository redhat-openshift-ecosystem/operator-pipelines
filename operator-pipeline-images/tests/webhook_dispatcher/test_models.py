from unittest.mock import MagicMock

from operatorcert.webhook_dispatcher.models import convert_to_webhook_event


def test_convert_to_webhook_event() -> None:
    request = MagicMock()
    request.headers = {
        "X-GitHub-Delivery": "1234567890",
        "X-GitHub-Event": "push",
        "X-GitHub-Signature": "sha256=88cd2108b5347d973cf39cdf9053d7dd42704876d8c9a9bd8e2d168259d3ddf7",
        "X-Hub-Example": "example",
    }
    payload = {
        "action": "push",
        "repository": {
            "full_name": "test/test",
        },
        "pull_request": {
            "number": 1,
        },
    }
    webhook_event = convert_to_webhook_event(payload, request)
    assert webhook_event.delivery_id == "1234567890"
    assert webhook_event.action == "push"
    assert webhook_event.payload == payload
    assert webhook_event.repository_full_name == "test/test"
    assert webhook_event.pull_request_number == 1
    assert webhook_event.received_at is not None
    assert webhook_event.processed is False
    assert webhook_event.processing_error is None
    assert webhook_event.request_headers == {
        "X-GitHub-Delivery": "1234567890",
        "X-GitHub-Event": "push",
        "X-GitHub-Signature": "sha256=88cd2108b5347d973cf39cdf9053d7dd42704876d8c9a9bd8e2d168259d3ddf7",
        "X-Hub-Example": "example",
    }
