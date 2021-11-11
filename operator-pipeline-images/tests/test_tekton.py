import pathlib
import textwrap

from operatorcert.tekton import PipelineRun, TaskRun

PARENT_DIR = pathlib.Path(__file__).parent.resolve()
PIPELINERUN_PATH = PARENT_DIR.joinpath("data/pipelinerun.json")
TASKRUNS_PATH = PARENT_DIR.joinpath("data/taskruns.json")


def test_taskrun():
    pr = PipelineRun.from_files(PIPELINERUN_PATH, TASKRUNS_PATH)

    # Successful TaskRun
    tr = pr.taskruns[-1]
    assert tr.pipelinetask == "set-github-status-pending"
    assert str(tr.start_time) == "2021-11-10 18:38:11+00:00"
    assert str(tr.completion_time) == "2021-11-10 18:38:19+00:00"
    assert tr.duration == "8 seconds"
    assert tr.status == TaskRun.SUCCEEDED

    # Missing conditions generate an unknown status
    tr.obj["status"]["conditions"] = []
    assert tr.status == TaskRun.UNKNOWN

    # Unknown condition
    tr = pr.taskruns[0]
    assert tr.status == TaskRun.UNKNOWN

    # Failed TaskRun
    tr = pr.taskruns[3]
    assert tr.status == TaskRun.FAILED


def test_pipelinerun():
    pr = PipelineRun.from_files(PIPELINERUN_PATH, TASKRUNS_PATH)

    assert pr.pipeline == "operator-hosted-pipeline"
    assert pr.name == "operator-hosted-pipeline-run-bvjls"
    assert str(pr.start_time) == "2021-11-10 18:38:09+00:00"
    assert pr.finally_taskruns == pr.taskruns[:2]

    md = textwrap.dedent(
        """
        # Pipeline Summary

        Pipeline: *operator-hosted-pipeline*
        PipelineRun: *operator-hosted-pipeline-run-bvjls*
        Start Time: *2021-11-10 18:38:09+00:00*

        ## Tasks

        | Status | Task | Start Time | Duration |
        | ------ | ---- | ---------- | -------- |
        | :heavy_check_mark: | set-github-status-pending | 2021-11-10 18:38:11+00:00 | 8 seconds |
        | :heavy_check_mark: | set-env | 2021-11-10 18:38:23+00:00 | 8 seconds |
        | :heavy_check_mark: | checkout | 2021-11-10 18:38:35+00:00 | 30 seconds |
        | :heavy_check_mark: | validate-pr-title | 2021-11-10 18:39:10+00:00 | 6 seconds |
        | :heavy_check_mark: | get-bundle-path | 2021-11-10 18:39:19+00:00 | 8 seconds |
        | :heavy_check_mark: | bundle-path-validation | 2021-11-10 18:39:29+00:00 | 14 seconds |
        | :heavy_check_mark: | content-hash | 2021-11-10 18:39:46+00:00 | 17 seconds |
        | :x: | certification-project-check | 2021-11-10 18:39:46+00:00 | 17 seconds |
    """
    )

    assert pr.markdown_summary() == md
