"""A common test suite for operator bundles"""
from collections.abc import Iterator
from typing import Any, List

from operator_repo import Bundle
from operator_repo.checks import CheckResult, Fail, Warn


class GraphLoopException(Exception):
    """
    Exception raised when a loop is detected in the update graph
    """


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


def check_upgrade_graph_loop(bundle: Bundle) -> Iterator[CheckResult]:
    """
    Detect loops in the upgrade graph

    Example:

    Channel beta: A -> B -> C -> B

    Args:
        bundle (Bundle): Operator bundle

    Yields:
        Iterator[CheckResult]: Failure if a loop is detected
    """
    all_channels: set[str] = set(bundle.channels)
    if bundle.default_channel is not None:
        all_channels.add(bundle.default_channel)
    operator = bundle.operator
    for channel in sorted(all_channels):
        visited: List[Bundle] = []
        try:
            channel_bundles = operator.channel_bundles(channel)
            try:
                graph = operator.update_graph(channel)
            except (NotImplementedError, ValueError) as exc:
                yield Fail(str(exc))
                return
            follow_graph(graph, channel_bundles[0], visited)
        except GraphLoopException as exc:
            yield Fail(str(exc))


def follow_graph(graph: Any, bundle: Bundle, visited: List[Bundle]) -> List[Bundle]:
    """
    Follow operator upgrade graph and raise exception if loop is detected

    Args:
        graph (Any): Operator update graph
        bundle (Bundle): Current bundle that started the graph traversal
        visited (List[Bundle]): List of bundles visited so far

    Raises:
        GraphLoopException: Graph loop detected

    Returns:
        List[Bundle]: List of bundles visited so far
    """
    if bundle in visited:
        visited.append(bundle)
        raise GraphLoopException(f"Upgrade graph loop detected for bundle: {visited}")
    if bundle not in graph:
        return visited

    visited.append(bundle)
    next_bundles = graph[bundle]
    for next_bundle in next_bundles:
        visited_copy = visited.copy()
        follow_graph(graph, next_bundle, visited_copy)
    return visited
