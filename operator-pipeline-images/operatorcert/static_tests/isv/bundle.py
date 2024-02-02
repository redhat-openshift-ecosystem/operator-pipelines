"""Static test for isv operator bundle."""

from collections.abc import Iterator

from operator_repo import Bundle
from operator_repo.checks import CheckResult, Fail, Warn

PRUNED_GRAPH_ERROR = (
    "olm.skipRange annotation is set but replaces field is not set in the CSV. "
    "The definition may lead to unintentional pruning of the update graph. "
    "https://olm.operatorframework.io/docs/concepts/olm-architecture/"
    "operator-catalog/creating-an-update-graph/#skiprange. "
    "If this is intentional, you can skip the check "
    "by adding `/test skip check_pruned_graph` comment to a pull request."
)


def check_pruned_graph(bundle: Bundle) -> Iterator[CheckResult]:
    """
    Check if the update graph is pruned when the bundle is added to the index

    Args:
        bundle (Bundle): Tested operator bundle
    """
    bundle_csv = bundle.csv
    replaces = bundle_csv.get("spec", {}).get("replaces")
    skip_range = (
        bundle_csv.get("metadata", {}).get("annotations", {}).get("olm.skipRange")
    )

    if skip_range and not replaces:
        channels = bundle.channels
        operator = bundle.operator

        for channel in channels:
            channel_bundles = operator.channel_bundles(channel)
            if len(channel_bundles) != 1:
                # TODO: This needs to be changed to Fail when the check
                # is publicly communicated
                yield Warn(PRUNED_GRAPH_ERROR)


def check_marketplace_annotation(bundle: Bundle) -> Iterator[CheckResult]:
    """
    Check if the bundle has the marketplace annotation set

    Args:
        bundle (Bundle): Tested operator bundle
    """
    repo = bundle.operator.repo
    organization = repo.config.get("organization")
    if organization != "redhat-marketplace":
        return

    annotation_package = bundle.annotations.get(
        "operators.operatorframework.io.bundle.package.v1"
    )

    csv_annotations = bundle.csv.get("metadata", {}).get("annotations", {})
    expected_remote_workflow = (
        "https://marketplace.redhat.com/en-us/operators/"
        f"{annotation_package}/pricing?utm_source=openshift_console"
    )
    expected_support_workflow = (
        "https://marketplace.redhat.com/en-us/operators/"
        f"{annotation_package}/support?utm_source=openshift_console"
    )

    remote_workflow = csv_annotations.get("marketplace.openshift.io/remote-workflow")
    support_workflow = csv_annotations.get("marketplace.openshift.io/support-workflow")

    if remote_workflow != expected_remote_workflow:
        yield Fail(
            "CSV marketplace.openshift.io/remote-workflow annotation is set to "
            f"'{remote_workflow}'. "
            f"Expected value is {expected_remote_workflow}. "
            "To fix this issue define the annotation in "
            "'manifests/*.clusterserviceversion.yaml' file."
        )
    if support_workflow != expected_support_workflow:
        yield Fail(
            "CSV marketplace.openshift.io/support-workflow annotation is set to "
            f"'{support_workflow}'. "
            f"Expected value is {expected_support_workflow}. "
            "To fix this issue define the annotation in "
            "'manifests/*.clusterserviceversion.yaml' file."
        )


def check_operator_name(bundle: Bundle) -> Iterator[CheckResult]:
    """
    Ensure that the operator name matches the CSV name

    Args:
        bundle (Bundle): Tested operator bundle
    """
    annotation_package = bundle.annotations.get(
        "operators.operatorframework.io.bundle.package.v1"
    )
    if annotation_package != bundle.csv_operator_name:
        yield Warn(
            f"Bundle package annotation is set to '{annotation_package}'. "
            f"Expected value is '{bundle.csv_operator_name}' based on the CSV name. "
            "To fix this issue define the annotation in "
            "'metadata/annotations.yaml' file that matches the CSV name."
        )
