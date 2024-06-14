"""
Operator checks for the community operator static test suite

An operator check is a function with a name starting with "check_"
and taking an Operator argument and yielding OperatorCheck objects
(either Fail or Warn) to describe the issues found in the given Operator.
"""

from collections.abc import Iterator

from operator_repo import Operator
from operator_repo.checks import CheckResult, Fail, Warn
from operatorcert.static_tests.helpers import skip_fbc


@skip_fbc
def check_operator_name_unique(operator: Operator) -> Iterator[CheckResult]:
    """Ensure all operator's bundles use the same operator name in their CSV"""
    names = {bundle.csv_operator_name for bundle in operator}
    if len(names) > 1:
        yield Fail(f"Bundles use multiple operator names: {names}")


def check_ci_upgrade_graph(operator: Operator) -> Iterator[CheckResult]:
    """Ensure the operator has a valid upgrade graph for ci.yaml"""
    upgrade_graph = operator.config.get("updateGraph")
    if not upgrade_graph:
        yield Warn(
            "The 'updateGraph' option is missing in ci.yaml. "
            "The default upgrade graph 'replaces-mode' will be used."
        )
    else:
        allowed_graphs = ["replaces-mode", "semver-mode"]
        if upgrade_graph not in allowed_graphs:
            yield Fail(
                f"The 'updateGraph' option in ci.yaml must be one of {allowed_graphs}"
            )
