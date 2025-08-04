from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from operatorcert.webhook_dispatcher.capacity_manager import OCPTektonCapacityManager
from kubernetes.config.config_exception import ConfigException


@patch("operatorcert.webhook_dispatcher.capacity_manager.config.load_kube_config")
@patch("operatorcert.webhook_dispatcher.capacity_manager.config.load_incluster_config")
@patch("operatorcert.webhook_dispatcher.capacity_manager.client.ApiClient")
def test_ocptekton_capacity_manager_k8s_client(
    mock_api_client: MagicMock,
    mock_load_incluster_config: MagicMock,
    mock_load_kube_config: MagicMock,
) -> None:
    capacity_manager = OCPTektonCapacityManager(
        pipeline_name="test-pipeline",
        max_capacity=10,
        namespace="test-namespace",
    )

    assert capacity_manager.k8s_client is not None
    mock_load_incluster_config.assert_called_once()
    mock_load_kube_config.assert_not_called()
    mock_api_client.assert_called_once()

    mock_load_incluster_config.reset_mock()
    mock_load_incluster_config.side_effect = ConfigException("test")

    assert capacity_manager.k8s_client is not None
    mock_load_kube_config.assert_called_once()

    mock_load_kube_config.side_effect = Exception("test")
    with pytest.raises(Exception):
        capacity_manager.k8s_client


@pytest.mark.asyncio
@patch(
    "operatorcert.webhook_dispatcher.capacity_manager.OCPTektonCapacityManager._get_running_tekton_pipelines_count"
)
async def test_ocptekton_capacity_manager_is_capacity_available(
    mock_get_running_tekton_pipelines_count: AsyncMock,
) -> None:
    capacity_manager = OCPTektonCapacityManager(
        pipeline_name="test-pipeline",
        max_capacity=10,
        namespace="test-namespace",
    )
    mock_get_running_tekton_pipelines_count.return_value = 5
    assert await capacity_manager.is_capacity_available() is True

    mock_get_running_tekton_pipelines_count.return_value = 11
    assert await capacity_manager.is_capacity_available() is False


@pytest.mark.asyncio
@patch(
    "operatorcert.webhook_dispatcher.capacity_manager.OCPTektonCapacityManager.k8s_client"
)
@patch("operatorcert.webhook_dispatcher.capacity_manager.client.CustomObjectsApi")
async def test_ocptekton_capacity_manager__get_running_tekton_pipelines_count(
    mock_custom_objects_api: MagicMock,
    mock_k8s_client: MagicMock,
) -> None:
    capacity_manager = OCPTektonCapacityManager(
        pipeline_name="test-pipeline",
        max_capacity=10,
        namespace="test-namespace",
    )
    mock_custom_objects_api.return_value.list_namespaced_custom_object.return_value = {
        "items": [
            {
                "metadata": {"name": "unknown-pipeline"},
                "spec": {"pipelineRef": {"name": "unknown-pipeline"}},
            },
            {
                "metadata": {"name": "test-pipeline-1"},
                "spec": {"pipelineRef": {"name": "test-pipeline"}},
                "status": {
                    "conditions": [
                        {"type": "Succeeded", "status": "Unknown", "reason": "Running"}
                    ]
                },
            },
            {
                "metadata": {"name": "test-pipeline-2"},
                "spec": {"pipelineRef": {"name": "test-pipeline"}},
                "status": {
                    "conditions": [
                        {"type": "Succeeded", "status": "Unknown", "reason": "Running"}
                    ]
                },
            },
            {
                "metadata": {"name": "test-pipeline-3"},
                "spec": {"pipelineRef": {"name": "test-pipeline"}},
                "status": {"conditions": [{"type": "Succeeded", "status": "True"}]},
            },
        ],
    }
    assert await capacity_manager._get_running_tekton_pipelines_count() == 2


@pytest.mark.asyncio
@patch(
    "operatorcert.webhook_dispatcher.capacity_manager.OCPTektonCapacityManager.k8s_client"
)
@patch("operatorcert.webhook_dispatcher.capacity_manager.client.CustomObjectsApi")
async def test_ocptekton_capacity_manager__get_running_tekton_pipelines_count_error(
    mock_custom_objects_api: MagicMock,
    mock_k8s_client: MagicMock,
) -> None:
    capacity_manager = OCPTektonCapacityManager(
        pipeline_name="test-pipeline",
        max_capacity=10,
        namespace="test-namespace",
    )
    mock_custom_objects_api.return_value.list_namespaced_custom_object.side_effect = (
        Exception("test")
    )
    with pytest.raises(Exception):  # pylint: disable=broad-exception-raised
        await capacity_manager._get_running_tekton_pipelines_count()
