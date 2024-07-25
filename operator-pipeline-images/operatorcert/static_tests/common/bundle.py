"""A common test suite for operator bundles"""

from collections.abc import Iterator
from typing import Any

from operator_repo import Bundle
from operator_repo.checks import CheckResult, Fail, Warn


def _check_consistency(
    my_name: str, all_names: set[str], other_names: set[str], result_description: str
) -> Iterator[CheckResult]:
    """Helper function for check_operator_name"""
    if len(other_names) == 1:
        # Operator names are consistent across other bundles
        common_name = other_names.pop()
        if common_name != my_name:
            # The new bundle has a different operator name
            msg = (
                f"Operator name {result_description} ({my_name})"
                f" does not match the name defined in other"
                f" bundles ({common_name})"
            )
            yield Fail(msg)
    else:
        # Other bundles have inconsistent operator names: let's just issue a warning
        msg = (
            f"Operator name {result_description} is not consistent across bundles:"
            f" {sorted(all_names)}"
        )
        yield Warn(msg)


def _safe_extract(bundles: set[Bundle], attribute: str) -> tuple[set[Any], set[Bundle]]:
    """Helper function to extract an attribute from all the bundles in a collection.
    If the extraction fails, keep track of which bundle caused the failure.
    Returns a tuple containing the set of attributes extracted and the set of bundles
    that failed the extraction"""
    results: set[Any] = set()
    bad: set[Bundle] = set()

    for bundle in bundles:
        try:
            results.add(getattr(bundle, attribute))
        except Exception:  # pylint: disable=broad-except
            bad.add(bundle)

    return results, bad


def check_operator_name(bundle: Bundle) -> Iterator[CheckResult]:
    """Check if the operator names used in CSV, metadata and filesystem are consistent
    in the bundle and across other operator's bundles"""
    try:
        if not bundle.metadata_operator_name:
            yield Fail("Bundle does not define the operator name in annotations.yaml")
            return
    except Exception:  # pylint: disable=broad-except
        yield Fail(f"Invalid operator name in annotations.yaml for {bundle}")
        return
    all_bundles = set(bundle.operator.all_bundles())
    all_metadata_operator_names, _ = _safe_extract(
        all_bundles, "metadata_operator_name"
    )
    all_csv_operator_names, bad = _safe_extract(all_bundles, "csv_operator_name")
    if bundle in bad:
        yield Fail(f"Invalid operator name in CSV for {bundle}")
        return
    other_bundles = all_bundles - {bundle}
    other_metadata_operator_names, _ = _safe_extract(
        other_bundles, "metadata_operator_name"
    )
    other_csv_operator_names, _ = _safe_extract(other_bundles, "csv_operator_name")
    if other_bundles:
        yield from _check_consistency(
            bundle.metadata_operator_name,
            all_metadata_operator_names,
            other_metadata_operator_names,
            "from annotations.yaml",
        )
        yield from _check_consistency(
            bundle.csv_operator_name,
            all_csv_operator_names,
            other_csv_operator_names,
            "from the CSV",
        )
    if bundle.metadata_operator_name != bundle.csv_operator_name:
        msg = (
            f"Operator name from annotations.yaml ({bundle.metadata_operator_name})"
            f" does not match the name defined in the CSV ({bundle.csv_operator_name})"
        )
        yield Warn(msg) if other_bundles else Fail(msg)
    if bundle.metadata_operator_name != bundle.operator_name:
        msg = (
            f"Operator name from annotations.yaml ({bundle.metadata_operator_name})"
            f" does not match the operator's directory name ({bundle.operator_name})"
        )
        yield Warn(msg) if other_bundles else Fail(msg)
