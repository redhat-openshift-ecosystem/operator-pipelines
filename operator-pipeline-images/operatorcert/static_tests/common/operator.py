"""A common test suite for operators"""

import json
import os

from collections.abc import Iterator
from jsonschema.validators import Draft202012Validator

from operator_repo import Operator
from operator_repo.checks import CheckResult, Fail

def check_validate_schema_ci_config(
    operator: Operator,
) -> Iterator[CheckResult]:
    """
    Validate the ci.yaml against the json schema
    """
    path_me = os.path.dirname(os.path.abspath(__file__))
    path_schema = os.path.join(path_me, "../../schemas/ci-schema.json")
    with open(path_schema, "r", encoding="utf-8") as file_schema:
        dict_schema = json.load(file_schema)
    # validate the ci.yaml against the json schema
    # use iter_errors() to collect and return all validation errors
    validator = Draft202012Validator(dict_schema)
    for ve in sorted(validator.iter_errors(operator.config), key=str):
        yield Fail(
            "Operator's 'ci.yaml' contains invalid data "
            f"which does not comply with the schema: {ve.message}"
        )
