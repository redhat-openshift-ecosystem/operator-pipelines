from pathlib import Path
from typing import Any, Dict, List

import pytest
from operator_repo import Repo
from operator_repo.checks import Fail, Warn
from operatorcert.static_tests.isv.bundle import (
    PRUNED_GRAPH_ERROR,
    check_marketplace_annotation,
    check_pruned_graph,
)
from tests.utils import bundle_files, create_files


@pytest.mark.parametrize(
    "skip_range,replaces,channels,expected",
    [
        pytest.param(None, None, ["alpha"], set(), id="No replaces, no skip_range"),
        pytest.param(None, "1.1", ["alpha"], set(), id="Replaces, no skip_range"),
        pytest.param(
            ">=1.0.2 <6.5.7",
            None,
            ["alpha"],
            {Warn(PRUNED_GRAPH_ERROR)},
            id="Skip range, no replaces, existing channel",
        ),
        pytest.param(
            ">=1.0.2 <6.5.7",
            None,
            ["xyz"],
            set(),
            id="Skip range, no replaces, new channel",
        ),
        pytest.param(
            ">=1.0.2 <6.5.7",
            None,
            ["xyz", "alpha"],
            {Warn(PRUNED_GRAPH_ERROR)},
            id="Skip range, no replaces, mix channel",
        ),
        pytest.param(
            ">=1.0.2 <6.5.7",
            "1.1",
            ["alpha"],
            set(),
            id="Skip range, replaces, existing channel",
        ),
    ],
)
def test_check_pruned_graph(
    skip_range: str, replaces: str, channels: List[str], expected: Any, tmp_path: Path
) -> None:
    # Create an existing bundle
    annotations = {
        "operators.operatorframework.io.bundle.channels.v1": "alpha,beta",
    }
    create_files(
        tmp_path, bundle_files("test-operator", "0.0.1", annotations=annotations)
    )

    # Create a bundle that will be checked
    csv: Dict[str, Any] = {}
    if skip_range:
        csv["metadata"] = {
            "annotations": {
                "olm.skipRange": skip_range,
            }
        }
    if replaces:
        csv["spec"] = {"replaces": replaces}

    annotations = {
        "operators.operatorframework.io.bundle.channels.v1": ",".join(channels),
    }

    create_files(
        tmp_path,
        bundle_files("test-operator", "0.0.2", csv=csv, annotations=annotations),
    )

    repo = Repo(tmp_path)
    bundle = repo.operator("test-operator").bundle("0.0.2")

    assert set(check_pruned_graph(bundle)) == expected


@pytest.mark.parametrize(
    "organization,remote_workflow_annotation,support_workflow_annotation,expected",
    [
        pytest.param("certified-operators", "", "", set(), id="Non-marketplace"),
        pytest.param(
            "redhat-marketplace",
            "https://marketplace.redhat.com/en-us/operators/package/pricing?utm_source="
            "openshift_console",
            "https://marketplace.redhat.com/en-us/operators/package/support?utm_source="
            "openshift_console",
            set(),
            id="Correct annotations",
        ),
        pytest.param(
            "redhat-marketplace",
            "",
            "https://marketplace.redhat.com/en-us/operators/package/support?utm_source="
            "openshift_console",
            {
                Fail(
                    "CSV marketplace.openshift.io/remote-workflow annotation is set "
                    "to ''. Expected value is https://marketplace.redhat.com/en-us/"
                    "operators/package/pricing?utm_source=openshift_console. "
                    "To fix this issue define the annotation in "
                    "'manifests/*.clusterserviceversion.yaml' file."
                )
            },
            id="Missing remote workflow annotation",
        ),
        pytest.param(
            "redhat-marketplace",
            "https://marketplace.redhat.com/en-us/operators/package/pricing?utm_source="
            "openshift_console",
            "",
            {
                Fail(
                    "CSV marketplace.openshift.io/support-workflow annotation is set "
                    "to ''. Expected value is https://marketplace.redhat.com/en-us"
                    "/operators/package/support?utm_source=openshift_console. "
                    "To fix this issue define the annotation in "
                    "'manifests/*.clusterserviceversion.yaml' file."
                )
            },
            id="Missing support workflow annotation",
        ),
    ],
)
def test_check_marketplace_annotation(
    organization: str,
    remote_workflow_annotation: str,
    support_workflow_annotation: Any,
    expected: Any,
    tmp_path: Path,
) -> None:
    annotations = {
        "marketplace.openshift.io/remote-workflow": remote_workflow_annotation,
        "marketplace.openshift.io/support-workflow": support_workflow_annotation,
    }

    create_files(
        tmp_path,
        bundle_files(
            "package", "0.0.1", csv={"metadata": {"annotations": annotations}}
        ),
        {"config.yaml": {"organization": organization}},
    )

    repo = Repo(tmp_path)
    bundle = repo.operator("package").bundle("0.0.1")

    assert set(check_marketplace_annotation(bundle)) == expected
