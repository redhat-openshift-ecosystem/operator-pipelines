"""A module for handling pipeline events in the webhook dispatcher."""

import logging

import httpx
from operatorcert.webhook_dispatcher.capacity_manager import (
    CapacityManager,
    OCPTektonCapacityManager,
)
from operatorcert.webhook_dispatcher.config import DispatcherConfigItem
from operatorcert.webhook_dispatcher.models import WebhookEvent

LOGGER = logging.getLogger("operator-cert")


class PipelineEvent:
    """
    Tekton pipeline event handler that manages the execution of pipelines
    based on the webhook events received from GitHub.
    """

    def __init__(self, event: WebhookEvent, config_item: DispatcherConfigItem | None):
        self.event = event
        self._config_item = config_item

    @property
    def config_item(self) -> DispatcherConfigItem:
        """
        Get the configuration item for the event.
        If the configuration item is not set, raise a ValueError.

        Returns:
            DispatcherConfigItem: A configuration item for the event
        """
        if self._config_item is None:
            raise ValueError("No configuration item found for event")
        return self._config_item

    def is_valid(self) -> bool:
        """
        Check if the event is valid for processing by checking if the configuration
        item is set.
        In case a configuration item is not set, the event can't be mapped to any of
        available configurations and thus can't be processed.

        Returns:
            bool: A True if the event is valid, False otherwise
        """
        return self._config_item is not None

    @property
    def capacity_manager(self) -> CapacityManager:
        """
        Factory method to create a capacity manager based on the configuration item.

        Returns:
            CapacityManager: A capacity manager instance based on the configuration item.
        """
        if self.config_item.capacity.type == "ocp_tekton":
            return OCPTektonCapacityManager(
                self.config_item.capacity.pipeline_name,
                self.config_item.capacity.max_capacity,
                self.config_item.capacity.namespace,
            )
        raise ValueError(f"Unsupported capacity type: {self.config_item.capacity.type}")

    async def is_capacity_available(self) -> bool:
        """
        Check if there is available capacity for the pipeline to be executed.

        Returns:
            bool: A True if capacity is available, False otherwise
        """
        LOGGER.info("Checking capacity for event %s", self.event.id)
        return await self.capacity_manager.is_capacity_available()

    async def trigger_pipeline(self) -> bool:
        """
        Trigger the pipeline execution by calling the configured callback URL.
        with the event payload and request headers.

        Returns:
            bool: A True if the pipeline was triggered successfully, False otherwise
        """
        http_client = httpx.AsyncClient()
        LOGGER.info(
            "Triggering pipeline for event %s by calling %s",
            self.event.id,
            self.config_item.callback_url,
        )
        response = await http_client.post(
            self.config_item.callback_url,
            json=self.event.payload,
            headers=self.event.request_headers,
        )
        if response.status_code != 202:
            LOGGER.error(
                "Failed to trigger pipeline for event %s: %s",
                self.event.id,
                response.text,
            )
            return False
        LOGGER.info(
            "Pipeline triggered successfully for event %s",
            self.event.id,
        )
        return True
