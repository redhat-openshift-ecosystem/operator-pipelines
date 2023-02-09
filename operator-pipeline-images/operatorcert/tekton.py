import datetime
import json
from typing import Any

import humanize
from dateutil.parser import isoparse


class TaskRun:
    """Representation of a Tekton Kubernetes TaskRun object"""

    # Possible status values
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"

    def __init__(self, obj: dict) -> None:
        self.obj = obj

    @property
    def pipelinetask(self) -> str:
        return self.obj["metadata"]["labels"]["tekton.dev/pipelineTask"]

    @property
    def start_time(self) -> datetime.datetime:
        return isoparse(self.obj["status"]["startTime"])

    @property
    def completion_time(self) -> datetime.datetime:
        return isoparse(self.obj["status"]["completionTime"])

    @property
    def duration(self) -> str:
        return humanize.naturaldelta(self.completion_time - self.start_time)

    @property
    def status(self) -> str:
        """
        Compute a status for the TaskRun.

        Returns:
            A simplified overall status
        """
        conditions = self.obj["status"]["conditions"]
        conditions = [x for x in conditions if x["type"].lower() == self.SUCCEEDED]

        # Figure out the status from the first succeeded condition, if it exists.
        if not conditions:
            return self.UNKNOWN

        condition_reason = conditions[0]["reason"].lower()

        if condition_reason.lower() == self.SUCCEEDED:
            return self.SUCCEEDED
        elif condition_reason.lower() == self.FAILED:
            return self.FAILED
        else:
            return self.UNKNOWN


class PipelineRun:
    """Representation of a Tekton Kubernetes PipelineRun object"""

    # TaskRun status mapped to markdown icons
    TASKRUN_STATUS_ICONS = {
        TaskRun.UNKNOWN: ":grey_question:",
        TaskRun.SUCCEEDED: ":heavy_check_mark:",
        TaskRun.FAILED: ":x:",
    }

    # Markdown summary template
    SUMMARY_TEMPLATE = """
# Pipeline Summary

Pipeline: *{pipeline}*
PipelineRun: *{pipelinerun}*
Start Time: *{start_time}*

## Tasks

| Status | Task | Start Time | Duration |
| ------ | ---- | ---------- | -------- |
{taskruns}
"""

    # Markdown TaskRun template
    TASKRUN_TEMPLATE = "| {icon} | {name} | {start_time} | {duration} |"

    def __init__(self, obj: dict, taskruns: list[TaskRun]) -> None:
        self.obj = obj
        self.taskruns = taskruns

    @classmethod
    def from_files(cls, obj_path: str, taskruns_path: str) -> "PipelineRun":
        """
        Construct a PipelineRun representation from Kubernetes objects.

        Args:
            obj_path: Path to a JSON formatted file with a PipelineRun definition
            taskruns_path: Path to a JSON formatted file with list of TaskRun definitions

        Returns:
            A PipelineRun object
        """
        with open(taskruns_path) as fh:
            taskruns = [TaskRun(tr) for tr in json.load(fh)]

        with open(obj_path) as fh:
            obj = json.load(fh)

        return cls(obj, taskruns)

    @property
    def pipeline(self) -> str:
        return self.obj["metadata"]["labels"]["tekton.dev/pipeline"]

    @property
    def name(self) -> str:
        return self.obj["metadata"]["name"]

    @property
    def start_time(self) -> datetime:
        return isoparse(self.obj["status"]["startTime"])

    @property
    def finally_taskruns(self) -> Any:
        """
        Returns all taskruns in the finally spec.

        Returns:
            A list of TaskRuns
        """
        pipeline_spec = self.obj["status"]["pipelineSpec"]
        finally_task_names = [task["name"] for task in pipeline_spec.get("finally", [])]
        return [tr for tr in self.taskruns if tr.pipelinetask in finally_task_names]

    def markdown_summary(self, include_final_tasks: bool = False) -> str:
        """
        Construct a markdown summary of the PipelineRun

        Args:
            include_final_tasks (bool): Set to true to summarize finally TaskRuns

        Returns:
            A summary in markdown format
        """
        # Sort TaskRuns by startTime
        taskruns = sorted(self.taskruns, key=lambda tr: tr.start_time)

        taskrun_parts = []

        for taskrun in taskruns:
            # Ignore final tasks if not desired
            if (not include_final_tasks) and taskrun in self.finally_taskruns:
                continue

            icon = self.TASKRUN_STATUS_ICONS[taskrun.status]

            tr = self.TASKRUN_TEMPLATE.format(
                icon=icon,
                name=taskrun.pipelinetask,
                start_time=taskrun.start_time,
                duration=taskrun.duration,
            )
            taskrun_parts.append(tr)

        taskruns_md = "\n".join(taskrun_parts)

        return self.SUMMARY_TEMPLATE.format(
            pipelinerun=self.name,
            pipeline=self.pipeline,
            start_time=self.start_time,
            taskruns=taskruns_md,
        )
