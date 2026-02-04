from datetime import datetime
from unittest.mock import MagicMock, patch

from flask import jsonify
from operatorcert.webhook_dispatcher import api
from operatorcert.webhook_dispatcher.api import app
from operatorcert.webhook_dispatcher.config import (
    CapacityConfig,
    DispatcherConfig,
    DispatcherConfigItem,
    Filter,
    SecurityConfig,
    WebhookDispatcherConfig,
)
from operatorcert.webhook_dispatcher.models import WebhookEvent


@patch("operatorcert.webhook_dispatcher.api.load_config")
def test_get_config(mock_load_config: MagicMock) -> None:
    mock_config = WebhookDispatcherConfig(
        dispatcher=DispatcherConfig(
            items=[
                DispatcherConfigItem(
                    name="test",
                    events=["test"],
                    full_repository_name="test/test",
                    callback_url="http://test.com",
                    capacity=CapacityConfig(
                        type="test",
                        pipeline_name="test",
                        max_capacity=10,
                        namespace="test",
                    ),
                    filter=Filter(cel_expression="body.action == 'pull_request'"),  # type: ignore[arg-type]
                )
            ],
        ),
        security=SecurityConfig(
            verify_signatures=False,
        ),
    )
    mock_load_config.return_value = mock_config

    config = api.get_config()
    assert config == mock_config


def test_event_to_dict() -> None:
    now = datetime.now()
    event = WebhookEvent(
        id=1,
        delivery_id="123",
        action="opened",
        repository_full_name="test/test",
        pull_request_number=123,
        processed=False,
        processing_error=None,
        received_at=now,
        processed_at=None,
        status="pending",
    )
    assert api.event_to_dict(event) == {
        "id": 1,
        "delivery_id": "123",
        "action": "opened",
        "repository_full_name": "test/test",
        "pull_request_number": 123,
        "processed": False,
        "processing_error": None,
        "received_at": now.isoformat(),
        "processed_at": None,
        "status": "pending",
    }


@patch("operatorcert.webhook_dispatcher.api.convert_to_webhook_event")
@patch("operatorcert.webhook_dispatcher.api.validate_github_webhook")
@patch("operatorcert.webhook_dispatcher.api.get_config")
@patch("operatorcert.webhook_dispatcher.api.get_database")
def test_github_pipeline_webhook(
    mock_get_database: MagicMock,
    mock_get_config: MagicMock,
    mock_validate_github_webhook: MagicMock,
    mock_convert_to_webhook_event: MagicMock,
) -> None:
    mock_validate_github_webhook.return_value = True
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_session
    mock_context.__exit__.return_value = None
    mock_get_database.return_value.get_session.return_value = mock_context

    mock_get_config.return_value = WebhookDispatcherConfig(
        dispatcher=DispatcherConfig(
            items=[
                DispatcherConfigItem(
                    name="test",
                    events=["test"],
                    full_repository_name="test/test",
                    callback_url="http://test.com",
                    capacity=CapacityConfig(
                        type="test",
                        pipeline_name="test",
                        max_capacity=10,
                        namespace="test",
                    ),
                    filter=None,
                )
            ],
        ),
        security=SecurityConfig(
            verify_signatures=False,
        ),
    )
    mock_convert_to_webhook_event.return_value = WebhookEvent(
        id=1,
        delivery_id="123",
        repository_full_name="test/test",
        pull_request_number=123,
        processed=False,
        processing_error=None,
        received_at=datetime.now(),
        processed_at=None,
        status="pending",
    )

    with app.test_client() as client:
        response = client.post(
            "/api/v1/webhooks/github-pipeline",
            json={
                "delivery_id": "123",
                "repository_full_name": "test/test",
                "pull_request_number": 123,
            },
        )
        assert response.status_code == 200
        assert response.json == {
            "status": "ok",
            "message": "Event received",
            **api.event_to_dict(mock_convert_to_webhook_event.return_value),
        }


@patch("operatorcert.webhook_dispatcher.api.validate_github_webhook")
@patch("operatorcert.webhook_dispatcher.api.get_config")
@patch("operatorcert.webhook_dispatcher.api.get_database")
def test_github_pipeline_webhook_invalid_event(
    mock_get_database: MagicMock,
    mock_get_config: MagicMock,
    mock_validate_github_webhook: MagicMock,
) -> None:

    with app.test_client() as client:
        mock_validate_github_webhook.return_value = (
            {"status": "rejected", "message": "Unsupported event"},
            400,
        )
        response = client.post(
            "/api/v1/webhooks/github-pipeline",
            json={"invalid": "data"},
        )
        assert response.status_code == 400
        assert response.json == {"status": "rejected", "message": "Unsupported event"}


@patch("operatorcert.webhook_dispatcher.api.convert_to_webhook_event")
@patch("operatorcert.webhook_dispatcher.api.validate_github_webhook")
@patch("operatorcert.webhook_dispatcher.api.get_config")
@patch("operatorcert.webhook_dispatcher.api.get_database")
def test_github_pipeline_webhook_invalid_event_type(
    mock_get_database: MagicMock,
    mock_get_config: MagicMock,
    mock_validate_github_webhook: MagicMock,
    mock_convert_to_webhook_event: MagicMock,
) -> None:

    with app.test_client() as client:
        mock_convert_to_webhook_event.return_value = None
        response = client.post(
            "/api/v1/webhooks/github-pipeline",
            json={"invalid": "data"},
        )
        assert response.status_code == 400
        assert response.json == {"status": "rejected", "message": "Unsupported event"}


@patch("operatorcert.webhook_dispatcher.api.get_database")
def test_events_status(mock_get_database: MagicMock) -> None:
    mock_db_session = MagicMock()
    mock_events = [
        WebhookEvent(
            id=1,
            delivery_id="123",
            repository_full_name="test/test",
            pull_request_number=123,
            processed=False,
            processing_error=None,
            received_at=datetime.now(),
            processed_at=None,
            status="pending",
        )
    ]
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_db_session
    mock_context.__exit__.return_value = None
    mock_get_database.return_value.get_session.return_value = mock_context

    mock_order_by = MagicMock()
    mock_order_by.offset.return_value.limit.return_value.all.return_value = mock_events
    mock_db_session.query.return_value.filter.return_value.order_by.return_value = (
        mock_order_by
    )

    mock_db_session.query.return_value.filter.return_value.count.return_value = 1
    with app.test_client() as client:
        response = client.get(
            "/api/v1/events/status?page=1&page_size=10&filter=status=pending"
        )
        assert response.status_code == 200
        assert response.json == {
            "status": "ok",
            "page": 1,
            "page_size": 10,
            "total_count": 1,
            "events": [api.event_to_dict(event) for event in mock_events],
        }


def test_get_ping() -> None:
    with app.test_client() as client:
        response = client.get("/api/v1/status/ping")
        assert response.status_code == 200
        assert response.json == {"status": "pong"}


@patch("operatorcert.webhook_dispatcher.api.get_database")
def test_get_db_status(mock_get_database: MagicMock) -> None:
    with app.test_client() as client:
        mock_get_database.return_value.health_check.return_value = True
        response = client.get("/api/v1/status/db")
        assert response.status_code == 200
        assert response.json == {"status": "ok", "message": "Database is running"}

        mock_get_database.return_value.health_check.return_value = False
        response = client.get("/api/v1/status/db")
        assert response.status_code == 500
        assert response.json == {
            "status": "error",
            "message": "Database health check failed",
        }
