from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import celpy.celparser
import pytest
from operatorcert.webhook_dispatcher.config import (
    CapacityConfig,
    DispatcherConfig,
    DispatcherConfigItem,
    Filter,
)
from operatorcert.webhook_dispatcher.dispatcher import EventDispatcher
from operatorcert.webhook_dispatcher.models import WebhookEvent
from operatorcert.webhook_dispatcher.pipeline_event import PipelineEvent


@pytest.fixture
def dispatcher() -> EventDispatcher:
    capacity_config = CapacityConfig(
        type="test",
        pipeline_name="test",
        max_capacity=10,
        namespace="test",
    )
    cel_filter = Filter(cel_expression="body.action == 'pull_request'")  # type: ignore[arg-type]

    return EventDispatcher(
        config=DispatcherConfig(
            items=[
                DispatcherConfigItem(
                    name="test1.0",
                    events=["pull_request"],
                    full_repository_name="test/test",
                    callback_url="http://test.com",
                    capacity=capacity_config,
                    filter=cel_filter,
                ),
                DispatcherConfigItem(
                    name="test1.1",
                    events=["pull_request"],
                    full_repository_name="test/test",
                    callback_url="http://test-another.com",
                    capacity=capacity_config,
                    filter=cel_filter,
                ),
                DispatcherConfigItem(
                    name="test2",
                    events=["push"],
                    full_repository_name="test/test2",
                    callback_url="http://test2.com",
                    capacity=capacity_config,
                    filter=cel_filter,
                ),
            ]
        )
    )


@pytest.mark.asyncio
@patch("operatorcert.webhook_dispatcher.dispatcher.asyncio.sleep")
@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.process_repository_events"
)
@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher._group_by_repository_and_pull_request"
)
@patch("operatorcert.webhook_dispatcher.dispatcher.get_database")
async def test_event_dispatcher_run(
    mock_get_database: MagicMock,
    mock_group_by_repository_and_pull_request: MagicMock,
    mock_process_repository_events: MagicMock,
    mock_time_sleep: MagicMock,
    dispatcher: EventDispatcher,
) -> None:
    mock_db_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_db_session
    mock_context.__exit__.return_value = None
    mock_get_database.return_value.get_session.return_value = mock_context

    mock_group_by_repository_and_pull_request.return_value = {
        "test/test": {
            1: [
                WebhookEvent(
                    id=1,
                    repository_full_name="test/test",
                    pull_request_number=1,
                    processed=False,
                    processing_error=None,
                    received_at=datetime.now(),
                    processed_at=None,
                    status="pending",
                )
            ]
        }
    }

    # To break from the loop
    mock_time_sleep.side_effect = Exception("test")

    with pytest.raises(Exception):
        await dispatcher.run()

        assert mock_time_sleep.call_count == 1
        mock_process_repository_events.assert_called_once_with(
            {
                1: [
                    WebhookEvent(
                        id=1,
                        repository_full_name="test/test",
                        pull_request_number=1,
                        processed=False,
                        processing_error=None,
                        received_at=datetime.now(),
                        processed_at=None,
                        status="pending",
                    )
                ]
            }
        )


@pytest.mark.asyncio
@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.process_pull_request_events"
)
async def test_process_repository_events(
    mock_process_pull_request_events: MagicMock,
    dispatcher: EventDispatcher,
) -> None:
    webhook_event = WebhookEvent(
        id=1,
        repository_full_name="test/test",
        pull_request_number=1,
        processed=False,
        processing_error=None,
    )

    await dispatcher.process_repository_events({1: [webhook_event]})
    mock_process_pull_request_events.assert_called_once_with([webhook_event])


@pytest.mark.asyncio
@patch("operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.cancel_event")
@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.abort_unsupported_event"
)
@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.process_pipeline_event"
)
@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.convert_to_pipeline_events"
)
@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.split_events_by_validity"
)
async def test_process_pull_request_events(
    mock_split_events_by_validity: MagicMock,
    mock_convert_to_pipeline_event: MagicMock,
    mock_process_pipeline_events: MagicMock,
    mock_abort_unsupported_event: MagicMock,
    mock_cancel_event: MagicMock,
    dispatcher: EventDispatcher,
) -> None:
    valid_event_1 = MagicMock()
    valid_event_1.received_at = datetime.now()

    valid_event_2 = MagicMock()
    valid_event_2.received_at = datetime.now() - timedelta(days=1)

    invalid_event = MagicMock()

    mock_split_events_by_validity.return_value = (
        [valid_event_1, valid_event_2],
        [invalid_event],
    )

    mock_pipeline_events = [MagicMock(), MagicMock()]

    mock_convert_to_pipeline_event.return_value = mock_pipeline_events

    await dispatcher.process_pull_request_events(
        [valid_event_1, valid_event_2, invalid_event]
    )

    mock_cancel_event.assert_called_once_with(valid_event_2)
    mock_abort_unsupported_event.assert_called_once_with(invalid_event)
    mock_process_pipeline_events.assert_has_calls(
        [
            call(mock_pipeline_events[0]),
            call(mock_pipeline_events[1]),
        ]
    )

    # Test only invalid events
    mock_split_events_by_validity.return_value = (
        [],
        [invalid_event],
    )
    mock_process_pipeline_events.reset_mock()
    mock_abort_unsupported_event.reset_mock()
    mock_cancel_event.reset_mock()
    await dispatcher.process_pull_request_events(
        [valid_event_1, valid_event_2, invalid_event]
    )

    mock_process_pipeline_events.assert_not_called()
    mock_abort_unsupported_event.assert_called_once_with(invalid_event)
    mock_cancel_event.assert_not_called()


@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.assign_configs_to_event"
)
def test_split_events_by_validity(
    mock_assign_configs_to_event: MagicMock,
    dispatcher: EventDispatcher,
) -> None:
    mock_assign_configs_to_event.side_effect = [
        [],
        [MagicMock(), MagicMock()],
        [MagicMock()],
    ]
    events = [MagicMock(), MagicMock(), MagicMock()]

    valid_events, invalid_events = dispatcher.split_events_by_validity(events)  # type: ignore
    assert len(valid_events) == 2
    assert len(invalid_events) == 1
    assert valid_events == events[1:]
    assert invalid_events == events[:1]


@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.match_cel_expression"
)
def test_assign_configs_to_event(
    mock_match_cel_expression: MagicMock, dispatcher: EventDispatcher
) -> None:
    event = WebhookEvent(
        id=1,
        repository_full_name="test/test",
        pull_request_number=1,
        action="pull_request",
        processed=False,
        processing_error=None,
    )

    configs = dispatcher.assign_configs_to_event(event)
    assert len(configs) == 2
    assert configs[0].name == "test1.0"
    assert configs[1].name == "test1.1"

    dispatcher.config.items[0].filter.cel_expression = "fake_expression"  # type: ignore
    mock_match_cel_expression.side_effect = [True, False]
    configs = dispatcher.assign_configs_to_event(event)
    assert len(configs) == 1
    assert configs[0].name == "test1.0"

    event = WebhookEvent(
        id=1,
        repository_full_name="test/test2",
        pull_request_number=1,
        action="pull_request",
        processed=False,
        processing_error=None,
    )
    configs = dispatcher.assign_configs_to_event(event)
    assert len(configs) == 0


@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.assign_configs_to_event"
)
def test_convert_to_pipeline_event(
    mock_assign_configs_to_event: MagicMock, dispatcher: EventDispatcher
) -> None:
    event = WebhookEvent(
        id=1,
        repository_full_name="test/test2",
        pull_request_number=1,
        action="push",
        processed=False,
        processing_error=None,
    )
    mock_assign_configs_to_event.return_value = [MagicMock(), MagicMock()]
    pipeline_events = dispatcher.convert_to_pipeline_events(event)
    assert len(pipeline_events) == 2
    assert (
        pipeline_events[0].config_item == mock_assign_configs_to_event.return_value[0]
    )
    assert (
        pipeline_events[1].config_item == mock_assign_configs_to_event.return_value[1]
    )
    assert pipeline_events[0].event == event
    assert pipeline_events[1].event == event


@pytest.mark.asyncio
@patch("operatorcert.webhook_dispatcher.dispatcher.asyncio.sleep")
@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.set_github_queued_label"
)
@patch("operatorcert.webhook_dispatcher.dispatcher.PipelineEvent.trigger_pipeline")
@patch("operatorcert.webhook_dispatcher.dispatcher.PipelineEvent.is_capacity_available")
async def test_process_pipeline_event(
    mock_is_capacity_available: AsyncMock,
    mock_trigger_pipeline: AsyncMock,
    mock_set_github_queued_label: MagicMock,
    mock_time_sleep: MagicMock,
    dispatcher: EventDispatcher,
) -> None:
    event = WebhookEvent(
        id=1,
        repository_full_name="test/test2",
        pull_request_number=1,
        action="push",
        processed=False,
        processing_error=None,
    )
    pipeline_event = PipelineEvent(event, MagicMock())
    mock_is_capacity_available.return_value = False

    # no capacity
    await dispatcher.process_pipeline_event(pipeline_event)
    mock_trigger_pipeline.assert_not_called()
    mock_set_github_queued_label.assert_called_once_with(pipeline_event)
    assert pipeline_event.event.processed == False

    # capacity available but trigger pipeline failed
    mock_trigger_pipeline.reset_mock()
    mock_set_github_queued_label.reset_mock()
    mock_trigger_pipeline.return_value = False
    mock_is_capacity_available.return_value = True
    await dispatcher.process_pipeline_event(pipeline_event)
    mock_trigger_pipeline.assert_called_once_with()
    mock_set_github_queued_label.assert_not_called()
    assert pipeline_event.event.processed == False

    # capacity available and trigger pipeline successful
    mock_trigger_pipeline.reset_mock()
    mock_trigger_pipeline.return_value = True
    await dispatcher.process_pipeline_event(pipeline_event)
    mock_trigger_pipeline.assert_called_once_with()
    assert pipeline_event.event.processed == True


def test_cancel_event(dispatcher: EventDispatcher) -> None:
    event = WebhookEvent(
        id=1,
        repository_full_name="test/test2",
        pull_request_number=1,
        action="push",
        processed=False,
        processing_error=None,
    )
    dispatcher.cancel_event(event)
    assert event.processed == True
    assert (
        event.processing_error
        == "Cancelled due to receiving a newer event for the same pull request"
    )
    assert event.status == "cancelled"
    assert event.processed_at is not None


def test_abort_unsupported_event(dispatcher: EventDispatcher) -> None:
    event = WebhookEvent(
        id=1,
        repository_full_name="test/test2",
        pull_request_number=1,
        action="push",
        processed=False,
        processing_error=None,
    )
    dispatcher.abort_unsupported_event(event)
    assert event.processed == True
    assert event.processing_error == "Unsupported event"
    assert event.status == "aborted"
    assert event.processed_at is not None


def test_group_by_repository_and_pull_request(dispatcher: EventDispatcher) -> None:
    events = [
        WebhookEvent(
            id=1,
            repository_full_name="test/test2",
            pull_request_number=1,
            action="push",
            processed=False,
            processing_error=None,
        ),
        WebhookEvent(
            id=2,
            repository_full_name="test/test2",
            pull_request_number=1,
            action="push",
            processed=False,
            processing_error=None,
        ),
        WebhookEvent(
            id=3,
            repository_full_name="test/test2",
            pull_request_number=2,
            action="push",
            processed=False,
            processing_error=None,
        ),
        WebhookEvent(
            id=4,
            repository_full_name="test/test3",
            pull_request_number=1,
            action="push",
            processed=False,
            processing_error=None,
        ),
    ]
    result = dispatcher._group_by_repository_and_pull_request(events)
    assert result == {
        "test/test2": {
            1: [events[0], events[1]],
            2: [events[2]],
        },
        "test/test3": {
            1: [events[3]],
        },
    }


@pytest.mark.parametrize(
    "cel_expression, payload, headers, expected_result",
    [
        pytest.param(
            'body.action == "pull_request"',
            {"action": "pull_request"},
            {},
            True,
            id="simple match",
        ),
        pytest.param(
            "("
            'body.action == "labeled"'
            ' && body.label.name == "pipeline/trigger-hosted"'
            ' && body.pull_request.base.ref == "main"'
            ")",
            {
                "action": "labeled",
                "label": {"name": "pipeline/trigger-hosted"},
                "pull_request": {"base": {"ref": "main"}},
            },
            {},
            True,
            id="complex match",
        ),
        pytest.param(
            "("
            'headers["X-GitHub-Event"] == "pull_request"'
            ' && body.action == "labeled"'
            ' && body.label.name == "pipeline/trigger-hosted"'
            ' && body.pull_request.base.ref == "main"'
            ")",
            {
                "action": "labeled",
                "label": {"name": "pipeline/trigger-hosted"},
                "pull_request": {"base": {"ref": "main"}},
            },
            {"X-GitHub-Event": "pull_request"},
            True,
            id="header match with complex body",
        ),
        pytest.param(
            "("
            'body.non_existing_field == "labeled"'
            ' && body.label.name == "pipeline/trigger-hosted"'
            ' && body.pull_request.base.ref == "main"'
            ")",
            {
                "action": "labeled",
                "label": {"name": "pipeline/trigger-hosted"},
                "pull_request": {"base": {"ref": "main"}},
            },
            {},
            False,
            id="non existing field in body",
        ),
        pytest.param(
            "1 / x",
            {},
            {},
            False,
            id="Runtime error, not defined variable x",
        ),
    ],
)
def test_match_cel_expression(
    cel_expression: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    expected_result: bool,
) -> None:
    capacity_config = CapacityConfig(
        type="test",
        pipeline_name="test",
        max_capacity=10,
        namespace="test",
    )

    item = DispatcherConfigItem(
        name="test1.0",
        events=["pull_request"],
        full_repository_name="test/test",
        callback_url="http://test.com",
        capacity=capacity_config,
        filter=Filter(cel_expression=cel_expression),  # type: ignore[arg-type]
    )
    dispatcher = EventDispatcher(config=DispatcherConfig(items=[item]))
    event = WebhookEvent(
        id=1,
        action="pull_request",
        repository_full_name="test/test",
        pull_request_number=1,
        processed=False,
        processing_error=None,
        payload=payload,
        request_headers={"X-GitHub-Event": "pull_request"},
    )

    result = dispatcher.match_cel_expression(event, item.filter.cel_expression)  # type: ignore
    assert result is expected_result


@patch("operatorcert.webhook_dispatcher.dispatcher.add_labels_to_pull_request")
@patch("operatorcert.webhook_dispatcher.dispatcher.Github")
@patch("operatorcert.webhook_dispatcher.dispatcher.Auth")
def test_set_github_queued_label(
    mock_auth: MagicMock,
    mock_github: MagicMock,
    mock_add_labels: MagicMock,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")
    config_item = DispatcherConfigItem(
        name="test1.0",
        events=["pull_request"],
        full_repository_name="test/test",
        callback_url="http://test.com",
        capacity=CapacityConfig(
            type="test",
            pipeline_name="my-pipeline",
            max_capacity=10,
            namespace="test",
        ),
    )
    event = WebhookEvent(
        id=1,
        repository_full_name="test/test",
        pull_request_number=1,
        action="push",
        processed=False,
        processing_error=None,
    )
    pipeline_event = PipelineEvent(event, config_item)
    mock_pull_request = MagicMock()
    mock_github.return_value.get_repo.return_value.get_pull.return_value = (
        mock_pull_request
    )
    EventDispatcher.set_github_queued_label(pipeline_event)

    mock_auth.Token.assert_called_once_with("test_token")
    mock_github.assert_called_once_with(auth=mock_auth.Token.return_value)

    mock_github.return_value.get_repo.assert_called_once_with("test/test")
    mock_github.return_value.get_repo.return_value.get_pull.assert_called_once_with(1)

    mock_add_labels.assert_called_once_with(mock_pull_request, ["my-pipeline/queued"])
