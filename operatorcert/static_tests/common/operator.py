"""A common test suite for operators"""

import json
import logging
import os
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

from jsonschema.validators import Draft202012Validator
from operatorcert.operator_repo import Operator
from operatorcert.operator_repo.checks import CheckResult, Fail
from operatorcert.redact import paths_with_leaks
from operatorcert.static_tests.helpers import get_affected_operator_files

LOGGER = logging.getLogger("operator-cert")


def check_leaks_in_changed_files(operator: Operator) -> Iterator[CheckResult]:
    """
    Scan pull-request-affected files under this operator for secret leaks using LeakTK.

    The list of affected files is provided by detect-changes via the static-tests
    entrypoint (see set_affected_operator_files). Catalog paths are not included.
    Fail messages report relative paths only and never include secret content.
    """
    affected_files = get_affected_operator_files()
    if not affected_files:
        return

    operator_prefix = f"operators/{operator.operator_name}/"
    repo_root = operator.repo.root
    paths_to_scan: list[Path] = []
    for rel_path in affected_files:
        if not rel_path.startswith(operator_prefix):
            continue
        absolute_path = repo_root / rel_path
        if absolute_path.is_file():
            paths_to_scan.append(absolute_path)

    if not paths_to_scan:
        return

    LOGGER.info(
        "Scanning %d affected file(s) under %s for secret leaks",
        len(paths_to_scan),
        operator_prefix,
    )
    try:
        leaky_paths = paths_with_leaks(*paths_to_scan)
    except Exception as exc:  # pylint: disable=broad-except
        # LeakTK stdout/errors can contain secret match text; never log or yield it.
        LOGGER.error(
            "LeakTK failed while scanning %d file(s) under %s (%s)",
            len(paths_to_scan),
            operator_prefix,
            type(exc).__name__,
        )
        yield Fail(
            "Secret leak scan failed due to an internal error. "
            "Re-run the pipeline or skip this check with the label "
            "tests/skip/check_leaks_in_changed_files if needed."
        )
        return

    for leaky_path in sorted(leaky_paths):
        try:
            rel_path = str(leaky_path.relative_to(repo_root))
        except ValueError:
            rel_path = str(leaky_path)
        yield Fail(
            f"Potential secret leak detected in {rel_path}. "
            "Remove secrets from the pull request before merging. "
            "To skip this check, add the label "
            "tests/skip/check_leaks_in_changed_files to the pull request."
        )


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
