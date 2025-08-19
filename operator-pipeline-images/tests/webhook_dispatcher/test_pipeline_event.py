from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from operatorcert.webhook_dispatcher.capacity_manager import OCPTektonCapacityManager
from operatorcert.webhook_dispatcher.config import CapacityConfig, DispatcherConfigItem
from operatorcert.webhook_dispatcher.models import WebhookEvent
from operatorcert.webhook_dispatcher.pipeline_event import PipelineEvent


@pytest.fixture
def pipeline_event() -> PipelineEvent:
    return PipelineEvent(
        event=WebhookEvent(
            id=1,
            repository_full_name="test/test",
            pull_request_number=1,
            action="push",
        ),
        config_item=DispatcherConfigItem(
            name="test",
            events=["push"],
            full_repository_name="test/test",
            callback_url="http://test.com",
            capacity=CapacityConfig(
                type="ocp_tekton",
                pipeline_name="test",
                max_capacity=1,
                namespace="test",
            ),
            filter=None,
        ),
    )


def test_config_item(pipeline_event: PipelineEvent) -> None:
    assert pipeline_event.config_item is not None

    pipeline_event._config_item = None
    with pytest.raises(ValueError):
        pipeline_event.config_item


def test_is_valid(pipeline_event: PipelineEvent) -> None:
    assert pipeline_event.is_valid()

    pipeline_event._config_item = None
    assert not pipeline_event.is_valid()


def test_capacity_manager(pipeline_event: PipelineEvent) -> None:
    manager = pipeline_event.capacity_manager
    assert isinstance(manager, OCPTektonCapacityManager)

    pipeline_event._config_item.capacity.type = "unknown"  # type: ignore
    with pytest.raises(ValueError):
        pipeline_event.capacity_manager


@pytest.mark.asyncio
@patch(
    "operatorcert.webhook_dispatcher.pipeline_event.OCPTektonCapacityManager.is_capacity_available"
)
async def test_is_capacity_available(
    mock_is_capacity_available: AsyncMock, pipeline_event: PipelineEvent
) -> None:
    assert await pipeline_event.is_capacity_available()

    mock_is_capacity_available.return_value = False
    assert not await pipeline_event.is_capacity_available()


@pytest.mark.asyncio
@patch("operatorcert.webhook_dispatcher.pipeline_event.httpx.AsyncClient")
async def test_trigger_pipeline(
    mock_httpx_client: MagicMock, pipeline_event: PipelineEvent
) -> None:
    mock_client_instance = MagicMock()
    mock_httpx_client.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_client_instance.post = AsyncMock(return_value=mock_response)

    result = await pipeline_event.trigger_pipeline()
    assert result is True

    mock_response.status_code = 400
    mock_client_instance.post.reset_mock()

    result = await pipeline_event.trigger_pipeline()
    assert result is False
