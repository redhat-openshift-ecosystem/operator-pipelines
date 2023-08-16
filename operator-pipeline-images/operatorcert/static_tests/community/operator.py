from collections.abc import Iterator

from operator_repo import Operator
from operator_repo.checks import CheckResult, Fail


def check_operator_name(operator: Operator) -> Iterator[CheckResult]:
    names = {bundle.csv_operator_name for bundle in operator}
    if len(names) > 1:
        yield Fail(f"Bundles use multiple operator names: {names}")
