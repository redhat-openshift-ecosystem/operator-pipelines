"""Static test for isv operator bundle."""

from collections.abc import Iterator

from operator_repo import Bundle
from operator_repo.checks import CheckResult, Warn

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
    print(skip_range, replaces)
    if skip_range and not replaces:
        channels = bundle.channels
        operator = bundle.operator

        for channel in channels:
            channel_bundles = operator.channel_bundles(channel)
            if len(channel_bundles) != 1:
                # TODO: This needs to be changed to Fail when the check
                # is publicly communicated
                yield Warn(PRUNED_GRAPH_ERROR)
