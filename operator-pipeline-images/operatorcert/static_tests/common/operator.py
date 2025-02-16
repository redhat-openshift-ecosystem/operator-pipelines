"""A common test suite for operators"""

import json
import os
from collections import defaultdict
from collections.abc import Iterator

from jsonschema.validators import Draft202012Validator
from operator_repo import Operator
from operator_repo.checks import CheckResult, Fail


def check_schema_operator_ci_config(
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


def check_catalog_usage_ci_config(operator: Operator) -> Iterator[CheckResult]:
    """
    Check if the catalog mapping in the ci.yaml is consistent and
    does not contain duplicates or multiple templates for the same catalog.
    """
    fbc_catalog_mapping = operator.config.get("fbc", {}).get("catalog_mapping", [])
    if not fbc_catalog_mapping:
        return
    catalog_to_template_mapping: dict[str, list[str]] = defaultdict(list)
    for template in fbc_catalog_mapping:
        catalogs = template.get("catalog_names", [])
        template_name = template.get("template_name")

        for catalog in catalogs:
            catalog_to_template_mapping[catalog].append(template_name)

    for catalog, templates in catalog_to_template_mapping.items():
        if len(templates) > 1:
            yield Fail(
                f"Operator's 'ci.yaml' contains multiple templates '{templates}' "
                f"for the same catalog '{catalog}'."
            )
