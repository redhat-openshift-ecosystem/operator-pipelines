"""Capacity Manager module for managing Tekton Pipeline capacity."""

import logging
from abc import ABC, abstractmethod

from kubernetes import client, config

LOGGER = logging.getLogger("operator-cert")


class CapacityManager(ABC):  # pylint: disable=too-few-public-methods
    """
    Abstract base class for capacity management.
    """

    @abstractmethod
    async def is_capacity_available(self) -> bool:  # pragma: no cover
        """
        Check if there is available capacity for the pipeline to be executed.

        Returns:
            bool: True if capacity is available, False otherwise
        """


class OCPTektonCapacityManager(CapacityManager):
    """
    A Tekton based capacity manager for OpenShift pipelines.
    A capacity is determined by the number of currently running Tekton PipelineRuns
    for the specified pipeline name in the given namespace.

    """

    def __init__(self, pipeline_name: str, max_capacity: int, namespace: str):
        self.pipeline_name = pipeline_name
        self.max_capacity = max_capacity
        self.namespace = namespace

        self._k8s_client = None

    @property
    def k8s_client(self) -> client.ApiClient:
        """
        Set up the Kubernetes client for interacting APIs.

        Returns:
            client.ApiClient: A Kubernetes API client instance
        """
        try:
            try:
                config.load_incluster_config()
            except config.config_exception.ConfigException:
                config.load_kube_config()
            self._k8s_client = client.ApiClient()
            return self._k8s_client

        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Failed to initialize Kubernetes client")
            raise

    async def is_capacity_available(self) -> bool:
        """
        Check if there is available capacity for the pipeline to be executed.
        The capacity is determined by the number of currently running Tekton PipelineRuns
        for the specified pipeline name in the given namespace.

        Returns:
            bool: A True if capacity is available, False otherwise
        """
        LOGGER.info(
            "Checking capacity for pipeline %s in namespace %s",
            self.pipeline_name,
            self.namespace,
        )
        pipeline_runs_count = await self._get_running_tekton_pipelines_count()
        is_free = pipeline_runs_count < self.max_capacity
        LOGGER.debug(
            "Running pipelines count: %s, max capacity: %s, is free: %s",
            pipeline_runs_count,
            self.max_capacity,
            is_free,
        )
        return is_free

    async def _get_running_tekton_pipelines_count(self) -> int:
        """
        Get the count of currently running Tekton pipelines for the specified
        pipeline name.

        Returns:
            int: A count of running pipelines
        """
        try:
            # Use the Kubernetes custom objects API to query Tekton PipelineRuns
            custom_objects_api = client.CustomObjectsApi(self.k8s_client)

            # Query PipelineRuns in the Tekton namespace
            pipeline_runs = custom_objects_api.list_namespaced_custom_object(
                group="tekton.dev",
                version="v1beta1",
                namespace=self.namespace,
                plural="pipelineruns",
            )

            # Count running pipelines
            running_count = 0
            for item in pipeline_runs.get("items", []):
                pipeline_name = item.get("spec", {}).get("pipelineRef", {}).get("name")
                if pipeline_name != self.pipeline_name:
                    continue

                status = item.get("status", {})
                conditions = status.get("conditions", [])

                # Check if pipeline is running
                for condition in conditions:
                    if (
                        condition.get("type") == "Succeeded"
                        and condition.get("status") == "Unknown"
                        and condition.get("reason") == "Running"
                    ):
                        running_count += 1
                        LOGGER.debug("Pipeline %s is running", item["metadata"]["name"])
                        break

            return running_count

        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Failed to get running Tekton pipelines count")
            raise
