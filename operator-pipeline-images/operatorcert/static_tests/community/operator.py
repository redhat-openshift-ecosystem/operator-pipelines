"""
    Operator checks for the community operator static test suite

    An operator check is a function with a name starting with "check_"
    and taking an Operator argument and yielding OperatorCheck objects
    (either Fail or Warn) to describe the issues found in the given Operator.
"""

from collections.abc import Iterator

from operator_repo import Operator
from operator_repo.checks import CheckResult, Fail


def check_operator_name(operator: Operator) -> Iterator[CheckResult]:
    """Ensure all operator's bundles use the same operator name in their CSV"""
    names = {bundle.csv_operator_name for bundle in operator}
    if len(names) > 1:
        yield Fail(f"Bundles use multiple operator names: {names}")
