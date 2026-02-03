"""
Event dispatcher module handles the processing of webhook events
and dispatches them to the appropriate pipelines based on the configuration.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

import celpy
import celpy.adapter
import celpy.evaluation
from github import Auth, Github
from operatorcert.github import add_labels_to_pull_request
from operatorcert.webhook_dispatcher.config import (
    DispatcherConfig,
    DispatcherConfigItem,
)
from operatorcert.webhook_dispatcher.database import get_db_session
from operatorcert.webhook_dispatcher.models import WebhookEvent
from operatorcert.webhook_dispatcher.pipeline_event import PipelineEvent

LOGGER = logging.getLogger("operator-cert")


class EventDispatcher:
    """
    Event dispatcher class for processing incoming webhook events
    and scheduling them for pipeline execution based on available capacity.
    """

    def __init__(self, config: DispatcherConfig):
        self.config = config

    async def run(self) -> None:
        """
        Run a dispatcher that continuously checks for new webhook events
        and processes them according to the configuration.
        """
        LOGGER.info("Starting event dispatcher.")

        while True:
            try:
                db_session = next(get_db_session())
                try:
                    # Get active webhook events that are not processed
                    webhook_events = (
                        db_session.query(WebhookEvent)
                        .filter(WebhookEvent.processed.is_(False))
                        .all()
                    )
                    LOGGER.debug("Found %s active webhook events", len(webhook_events))
                    grouped_events = self._group_by_repository_and_pull_request(
                        webhook_events
                    )

                    for repository_name, repository_events in grouped_events.items():
                        LOGGER.info(
                            "Processing repository %s with %s pull request events",
                            repository_name,
                            len(repository_events),
                        )
                        await self.process_repository_events(repository_events)
                    db_session.commit()
                finally:
                    db_session.close()

            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Error in event dispatcher")
            await asyncio.sleep(5)

    async def process_repository_events(
        self, repository_events: dict[int, list[WebhookEvent]]
    ) -> None:
        """
        Process events for a specific repository.

        Args:
            repository_events (dict[int, list[WebhookEvent]]): A dictionary
            where keys are pull request numbers and values are lists of
            WebhookEvent objects for that pull request.
        """

        for pull_request_events in repository_events.values():
            await self.process_pull_request_events(pull_request_events)

    async def process_pull_request_events(
        self, pull_request_events: list[WebhookEvent]
    ) -> None:
        """
        Process events for a specific pull request.

        Args:
            pull_request_events (list[WebhookEvent]): A list of WebhookEvent objects
            for a specific pull request.
        """
        valid_events, invalid_events = self.split_events_by_validity(
            pull_request_events
        )
        for event in invalid_events:
            # Events produced by the Github that are not supported by the dispatcher
            # are aborted
            self.abort_unsupported_event(event)

        if not valid_events:
            return

        sorted_events = sorted(valid_events, key=lambda x: x.received_at, reverse=True)

        # First event is the latest one, so it will be processed
        # All other events are cancelled as duplicates
        event_to_process = sorted_events[0]
        events_to_cancel = sorted_events[1:]

        for event in events_to_cancel:
            self.cancel_event(event)

        pipeline_events_to_process = self.convert_to_pipeline_events(event_to_process)
        for pipeline_event in pipeline_events_to_process:
            await self.process_pipeline_event(pipeline_event)

    def split_events_by_validity(
        self, events: list[WebhookEvent]
    ) -> tuple[list[WebhookEvent], list[WebhookEvent]]:
        """
        Split events into valid and invalid events based on whether there is
        a configuration item that matches the event.

        Args:
            events (list[WebhookEvent]): A list of WebhookEvent objects to split.

        Returns:
            tuple[list[WebhookEvent], list[WebhookEvent]]: A tuple containing two lists:
            the first list contains valid events, and the second list contains invalid events.
        """
        valid_events = []
        invalid_events = []
        for event in events:
            configs = self.assign_configs_to_event(event)
            if configs:
                valid_events.append(event)
            else:
                invalid_events.append(event)
        return valid_events, invalid_events

    def assign_configs_to_event(
        self, event: WebhookEvent
    ) -> list[DispatcherConfigItem]:
        """
        Assign the configuration items to the event based on the repository name
        and action type.

        Args:
            event (WebhookEvent): A WebhookEvent object containing event data.

        Returns:
            list[DispatcherConfigItem]: A list of configuration items that matches the event.
        """
        configs = []
        for item in self.config.items:
            if event.repository_full_name != item.full_repository_name:
                continue
            if event.action not in item.events:
                continue
            if item.filter and item.filter.cel_expression:
                if not self.match_cel_expression(
                    event,
                    item.filter.cel_expression,
                ):
                    LOGGER.debug(
                        "Event %s did not match the CEL expression for config %s",
                        event.id,
                        item.name,
                    )
                    continue
            configs.append(item)
        return configs

    def match_cel_expression(
        self,
        event: WebhookEvent,
        cel_expression: celpy.Expression[Any],
    ) -> bool:
        """
        Match the event against a CEL expression and return whether it matches.

        Args:
            event (WebhookEvent): A WebhookEvent object containing event data.
            cel_expression (celpy.Expression): A CEL expression to match against the event.

        Returns:
            bool: A True if the event matches the CEL expression, False otherwise.
        """
        try:
            env = celpy.Environment()
            program = env.program(cel_expression)

            context = {
                "body": celpy.adapter.json_to_cel(event.payload),
                "headers": celpy.adapter.json_to_cel(event.request_headers),
            }

            result = program.evaluate(context)
            return bool(result)
        except (celpy.evaluation.CELEvalError, celpy.evaluation.CELUnsupportedError):
            LOGGER.exception("Failed to evaluate CEL.")
            return False

    def convert_to_pipeline_events(self, event: WebhookEvent) -> list[PipelineEvent]:
        """
        Convert a WebhookEvent to a PipelineEvents with the assigned configuration.

        Args:
            event (WebhookEvent): A WebhookEvent object to convert.

        Returns:
            list[PipelineEvent]: A list of PipelineEvent objects initialized with the event
            and the assigned configuration items.
        """
        configs = self.assign_configs_to_event(event)
        return [PipelineEvent(event, config) for config in configs]

    async def process_pipeline_event(self, pipeline_event: PipelineEvent) -> None:
        """
        Process a PipelineEvent by checking capacity and triggering the pipeline.

        Args:
            pipeline_event (PipelineEvent): A PipelineEvent object to process.
        """
        event = pipeline_event.event
        LOGGER.info(
            "Processing event %s for pull request %s in repository %s",
            event.id,
            event.pull_request_number,
            event.repository_full_name,
        )
        if not await pipeline_event.is_capacity_available():
            LOGGER.debug(
                "There is not enough capacity to process the event %s", event.id
            )
            if event.status != "queued":
                # Mark the event as queued and set the GitHub label
                self.set_github_queued_label(pipeline_event)
                event.status = "queued"

            # Waiting for a next loop to process the event
            return

        result = await pipeline_event.trigger_pipeline()
        if not result:
            LOGGER.error("Failed to trigger pipeline for event %s", event.id)
            # Don't mark the event as processed, so it will be retried in the next loop
            return

        # Give some time for the pipeline to start so it can be tracked
        # by the capacity manager in the next loop
        await asyncio.sleep(10)

        event.processed = True
        event.processing_error = None
        event.processed_at = datetime.now()
        event.status = "processed"
        return

    def cancel_event(self, event: WebhookEvent) -> None:
        """
        Cancel an event by marking it as processed and setting an error message.
        Events are cancelled if a newer event for the same pull request is received.

        Args:
            event (WebhookEvent): A WebhookEvent object to cancel.
        """
        LOGGER.info(
            "Cancelling event %s for pull request %s in repository %s because of "
            "receiving a newer event",
            event.id,
            event.pull_request_number,
            event.repository_full_name,
        )
        event.processed = True
        event.processing_error = (
            "Cancelled due to receiving a newer event for the same pull request"
        )
        event.status = "cancelled"
        event.processed_at = datetime.now()

    def abort_unsupported_event(self, event: WebhookEvent) -> None:
        """
        Abort an unsupported event by marking it as processed and setting an
        error message.

        Args:
            event (WebhookEvent): A WebhookEvent object to abort.
        """
        LOGGER.info(
            "Aborting unsupported event %s for pull request %s in repository %s",
            event.id,
            event.pull_request_number,
            event.repository_full_name,
        )
        event.processed = True
        event.processing_error = "Unsupported event"
        event.status = "aborted"
        event.processed_at = datetime.now()

    def _group_by_repository_and_pull_request(
        self, webhook_events: list[WebhookEvent]
    ) -> dict[str, dict[int, list[WebhookEvent]]]:
        """
        Group webhook events by repository and pull request number.

        Args:
            webhook_events (list[WebhookEvent]): A list of WebhookEvent objects.

        Returns:
            dict[str, dict[int, list[WebhookEvent]]]: Groped events by repository
            name and pull request number.
        """
        output: dict[str, dict[int, list[WebhookEvent]]] = {}
        for event in webhook_events:
            if event.repository_full_name not in output:
                output[event.repository_full_name] = {}
            if event.pull_request_number not in output[event.repository_full_name]:
                output[event.repository_full_name][event.pull_request_number] = []
            output[event.repository_full_name][event.pull_request_number].append(event)
        return output

    @staticmethod
    def set_github_queued_label(pipeline_event: PipelineEvent) -> None:
        """
        Set the "github/queued" label on the pull request associated with the event.

        Args:
            event (WebhookEvent): A WebhookEvent object for which to set the label.
        """
        github_auth = Auth.Token(os.environ.get("GITHUB_TOKEN") or "")
        github = Github(auth=github_auth)

        event = pipeline_event.event
        label = f"{pipeline_event.config_item.capacity.pipeline_name}/queued"

        repo = github.get_repo(event.repository_full_name)
        pull_request = repo.get_pull(event.pull_request_number)
        add_labels_to_pull_request(pull_request, [label])
        LOGGER.info("Set label '%s' on pull request %s", label, pull_request.html_url)
