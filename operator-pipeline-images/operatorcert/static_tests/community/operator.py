"""
Operator checks for the community operator static test suite

An operator check is a function with a name starting with "check_"
and taking an Operator argument and yielding OperatorCheck objects
(either Fail or Warn) to describe the issues found in the given Operator.
"""

from collections.abc import Iterator
from typing import Dict, Optional

from operator_repo import Operator, Bundle
from operator_repo.checks import CheckResult, Fail, Warn
from operatorcert.static_tests.helpers import skip_fbc


@skip_fbc
def check_operator_name_unique(operator: Operator) -> Iterator[CheckResult]:
    """Ensure all operator's bundles use the same operator name in their CSV"""
    names = {bundle.csv_operator_name for bundle in operator}
    if len(names) > 1:
        yield Fail(f"Bundles use multiple operator names: {names}")


@skip_fbc
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


@skip_fbc
def check_upgrade_graph_loop(operator: Operator) -> Iterator[CheckResult]:
    """
    Detect loops in the upgrade graph

    Example:

    Channel beta: A -> B -> C -> B

    Args:
        operator (Operator): Operator

    Yields:
        Iterator[CheckResult]: Failure if a loop is detected
    """
    all_channels: set[str] = set()
    for bundle in operator.all_bundles():
        all_channels.update(bundle.channels)
        if bundle.default_channel is not None:
            all_channels.add(bundle.default_channel)
    for channel in sorted(all_channels):
        try:
            graph = operator.update_graph(channel)
        except (NotImplementedError, ValueError) as exc:
            yield Fail(str(exc))
            return
        back_edge = has_cycle(graph)
        if back_edge is not None:
            node_from, node_to = back_edge
            yield Fail(f"Upgrade graph loop detected: {node_from} -> {node_to}")


def has_cycle(graph: Dict[Bundle, set[Bundle]]) -> Optional[tuple[Bundle, Bundle]]:
    """
    Detects cycles in an update graph using regular BFS

    Args:
        graph: Upgrade graph

    Returns:
        - None if no cycle is detected
        - A tuple representing the edge (from_bundle, to_bundle) causing the cycle
    """

    def dfs(
        node: Bundle, visited: set[Bundle], rec_stack: set[Bundle]
    ) -> Optional[tuple[Bundle, Bundle]]:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                result = dfs(neighbor, visited, rec_stack)
                if result:
                    return result
            elif neighbor in rec_stack:
                return (node, neighbor)

        rec_stack.remove(node)
        return None

    visited: set[Bundle] = set()
    rec_stack: set[Bundle] = set()

    for node in graph:
        if node not in visited:
            result = dfs(node, visited, rec_stack)
            if result:
                return result

    return None
