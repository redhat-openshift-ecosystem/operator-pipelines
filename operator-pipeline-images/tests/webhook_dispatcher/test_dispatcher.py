from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from operatorcert.webhook_dispatcher.config import (
    CapacityConfig,
    DispatcherConfig,
    DispatcherConfigItem,
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
    return EventDispatcher(
        config=DispatcherConfig(
            items=[
                DispatcherConfigItem(
                    name="test",
                    events=["test"],
                    full_repository_name="test/test",
                    callback_url="http://test.com",
                    capacity=capacity_config,
                ),
                DispatcherConfigItem(
                    name="test2",
                    events=["push"],
                    full_repository_name="test/test2",
                    callback_url="http://test2.com",
                    capacity=capacity_config,
                ),
            ]
        )
    )


@pytest.mark.asyncio
@patch("operatorcert.webhook_dispatcher.dispatcher.time.sleep")
@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.process_repository_events"
)
@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher._group_by_repository_and_pull_request"
)
@patch("operatorcert.webhook_dispatcher.dispatcher.get_db_session")
async def test_event_dispatcher_run(
    mock_get_db_session: MagicMock,
    mock_group_by_repository_and_pull_request: MagicMock,
    mock_process_repository_events: MagicMock,
    mock_time_sleep: MagicMock,
    dispatcher: EventDispatcher,
) -> None:
    mock_db_session = MagicMock()
    mock_get_db_session.return_value.__iter__.return_value = iter([mock_db_session])
    mock_get_db_session.return_value.__next__.return_value = mock_db_session

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

    mock_db_session.commit.side_effect = Exception("test")
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
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.convert_to_pipeline_event"
)
async def test_process_pull_request_events(
    mock_convert_to_pipeline_event: MagicMock,
    mock_process_pipeline_event: MagicMock,
    mock_abort_unsupported_event: MagicMock,
    mock_cancel_event: MagicMock,
    dispatcher: EventDispatcher,
) -> None:
    valid_event_1 = MagicMock()
    valid_event_1.is_valid.return_value = True
    valid_event_1.event.received_at = datetime.now()

    valid_event_2 = MagicMock()
    valid_event_2.is_valid.return_value = True
    valid_event_2.event.received_at = datetime.now() - timedelta(days=1)

    invalid_event = MagicMock()
    invalid_event.is_valid.return_value = False

    mock_convert_to_pipeline_event.side_effect = [
        valid_event_1,
        valid_event_2,
        invalid_event,
    ]

    await dispatcher.process_pull_request_events(
        [MagicMock(), MagicMock(), MagicMock()]
    )

    mock_cancel_event.assert_called_once_with(valid_event_2.event)
    mock_abort_unsupported_event.assert_called_once_with(invalid_event.event)
    mock_process_pipeline_event.assert_called_once_with(valid_event_1)


def test_assign_config_to_event(dispatcher: EventDispatcher) -> None:
    event = WebhookEvent(
        id=1,
        repository_full_name="test/test2",
        pull_request_number=1,
        action="push",
        processed=False,
        processing_error=None,
    )
    config = dispatcher.assign_config_to_event(event)
    assert config is not None
    assert config.name == "test2"

    event = WebhookEvent(
        id=1,
        repository_full_name="test/test2",
        pull_request_number=1,
        action="pull_request",
        processed=False,
        processing_error=None,
    )
    config = dispatcher.assign_config_to_event(event)
    assert config is None


@patch(
    "operatorcert.webhook_dispatcher.dispatcher.EventDispatcher.assign_config_to_event"
)
def test_convert_to_pipeline_event(
    mock_assign_config_to_event: MagicMock, dispatcher: EventDispatcher
) -> None:
    event = WebhookEvent(
        id=1,
        repository_full_name="test/test2",
        pull_request_number=1,
        action="push",
        processed=False,
        processing_error=None,
    )
    mock_assign_config_to_event.return_value = MagicMock()
    pipeline_event = dispatcher.convert_to_pipeline_event(event)
    assert pipeline_event.config_item == mock_assign_config_to_event.return_value
    assert pipeline_event.event == event


@pytest.mark.asyncio
@patch("operatorcert.webhook_dispatcher.dispatcher.PipelineEvent.trigger_pipeline")
@patch("operatorcert.webhook_dispatcher.dispatcher.PipelineEvent.is_capacity_available")
async def test_process_pipeline_event(
    mock_is_capacity_available: AsyncMock,
    mock_trigger_pipeline: AsyncMock,
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
    assert pipeline_event.event.processed == False

    # capacity available but trigger pipeline failed
    mock_trigger_pipeline.reset_mock()
    mock_trigger_pipeline.return_value = False
    mock_is_capacity_available.return_value = True
    await dispatcher.process_pipeline_event(pipeline_event)
    mock_trigger_pipeline.assert_called_once_with()
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
