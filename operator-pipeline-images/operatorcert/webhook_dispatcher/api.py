"""
Webhook API for handling GitHub pipeline events.
"""

import logging
import os
from typing import Any

import flask
from flask import jsonify, request

from operatorcert.webhook_dispatcher.config import load_config
from operatorcert.webhook_dispatcher.database import get_database, get_db_session
from operatorcert.webhook_dispatcher.models import (
    WebhookEvent,
    convert_to_webhook_event,
)
from operatorcert.webhook_dispatcher.security import validate_github_webhook

_CONFIG = None

LOGGER = logging.getLogger("operator-cert")
app = flask.Flask(__name__)


def get_config() -> Any:
    """
    Load and return the configuration.
    If the configuration is already loaded, return the cached version.
    """
    # singleton pattern for configuration loading
    global _CONFIG  # pylint: disable=global-statement
    if _CONFIG is None:
        _CONFIG = load_config(
            os.getenv("WEBHOOK_DISPATCHER_CONFIG", "dispatcher_config.json")
        )
    return _CONFIG


def event_to_dict(event: WebhookEvent) -> dict[str, Any]:
    """
    Convert a WebhookEvent object to a dictionary.
    """
    return {
        "id": event.id,
        "delivery_id": event.delivery_id,
        "action": event.action,
        "repository_full_name": event.repository_full_name,
        "pull_request_number": event.pull_request_number,
        "processed": event.processed,
        "processing_error": event.processing_error,
        "received_at": event.received_at.isoformat(),
        "processed_at": event.processed_at.isoformat() if event.processed_at else None,
        "status": event.status,
    }


@app.route("/api/v1/webhooks/github-pipeline", methods=["POST"])
def github_pipeline_webhook() -> Any:
    """
    Receive GitHub webhook events for pipeline execution.

    Returns:
        Any: A JSON response indicating the status of the event processing.
    """
    payload = request.get_json()
    config = get_config()
    result = validate_github_webhook(request, config.security)
    if isinstance(result, tuple):
        LOGGER.debug("GitHub webhook validation failed: %s", result)
        return jsonify(result[0]), result[1]
    webhook_event = convert_to_webhook_event(payload, request)
    if webhook_event is None:
        return jsonify({"status": "rejected", "message": "Unsupported event"}), 400

    db_session = next(get_db_session())
    db_session.add(webhook_event)
    db_session.commit()

    return (
        jsonify(
            {
                "status": "ok",
                "message": "Event received",
                **event_to_dict(webhook_event),
            }
        ),
        200,
    )


@app.route("/api/v1/events/status", methods=["GET"])
def events_status() -> Any:
    """
    Get a summary of webhook events.

    Returns:
        Any: A JSON response containing the status of webhook events.
    """
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 10, type=int)
    request_filter = request.args.get("filter", "")

    db_filter = []

    for item in request_filter.split(";"):
        if "=" in item:
            key, val = item.split("=")
            db_filter.append(getattr(WebhookEvent, key) == val)

    db_session = next(get_db_session())

    events = (
        db_session.query(WebhookEvent)
        .filter(*db_filter)
        .order_by(WebhookEvent.received_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_count = db_session.query(WebhookEvent).filter(*db_filter).count()

    output = []
    for event in events:
        output.append(event_to_dict(event))

    return (
        jsonify(
            {
                "status": "ok",
                "events": output,
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
            }
        ),
        200,
    )


@app.route("/api/v1/status/ping", methods=["GET"])
def get_ping() -> Any:
    """
    Health check endpoint to verify the API is running.

    Returns:
        Any: A JSON response indicating the API status.
    """
    return jsonify({"status": "pong"}), 200


@app.route("/api/v1/status/db", methods=["GET"])
def get_db_status() -> Any:
    """
    Health check endpoint to verify the database is running.

    Returns:
        Any: A JSON response indicating the API status.
    """
    db_manager = get_database()
    if db_manager.health_check():
        return jsonify({"status": "ok", "message": "Database is running"}), 200
    return (
        jsonify({"status": "error", "message": "Database health check failed"}),
        500,
    )
