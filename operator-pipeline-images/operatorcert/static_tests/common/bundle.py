"""A common test suite for operator bundles"""

from collections.abc import Iterator

from operator_repo import Bundle
from operator_repo.checks import CheckResult, Warn


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
