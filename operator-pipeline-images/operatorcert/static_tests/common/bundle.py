"""A common test suite for operator bundles"""

import json
import os
from typing import Any

from collections.abc import Iterator
from jsonschema.validators import Draft202012Validator

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


def _check_semver_allowed_channels(
    template_in_mapping: dict[str, Any], release_config_template: dict[str, Any]
) -> Iterator[CheckResult]:
    """
    Check if the channels in the semver catalog template are allowed.
    The semver is very strict about the allowed channels. The only allowed
    channels are: Fast, Candidate, Stable.

    Args:
        template_in_mapping (dict[str, Any]): A catalog template from the ci.yaml file
        release_config_template (dict[str, Any]): A release config for a bundle

    Yields:
        Iterator[CheckResult]: A check result if the channels are not allowed
    """
    if template_in_mapping["type"] != "olm.semver":
        return
    allowed_channels_in_semver = ["Fast", "Candidate", "Stable"]
    if set(release_config_template["channels"]).issubset(
        set(allowed_channels_in_semver)
    ):
        return
    yield Fail(
        "Bundle's 'release-config.yaml' contains a semver catalog template "
        f"'{release_config_template['template_name']}' with invalid channels: "
        f"{release_config_template['channels']}. "
        f"Allowed channels are: {allowed_channels_in_semver}. "
        "Follow olm [documentation](https://olm.operatorframework.io/docs/"
        "reference/catalog-templates/#specification) to see more details "
        "about semver template."
    )


def check_bundle_release_config(bundle: Bundle) -> Iterator[CheckResult]:
    """
    Check if the bundle release config is in a right format and consistent
    with the ci.yaml file
    """
    if not bundle.release_config:
        return
    ci_file = bundle.operator.config
    fbc_enabled = ci_file.get("fbc", {}).get("enabled", False)
    if not fbc_enabled:
        yield Fail(
            "Bundle's 'release-config.yaml' is used but FBC is not enabled "
            "for the operator. Update the 'fbc.enabled' field in the ci.yaml file."
        )
        return
    catalog_mapping = ci_file.get("fbc", {}).get("catalog_mapping", [])
    template_names_in_mapping = {
        template["template_name"]: template for template in catalog_mapping
    }
    for template in bundle.release_config["catalog_templates"]:
        if template["template_name"] not in template_names_in_mapping:
            yield Fail(
                "Bundle's 'release-config.yaml' contains a catalog template "
                f"'{template['template_name']}' that is not defined in the ci.yaml file "
                "under 'catalog_mapping'. Add the template to the 'catalog_mapping."
            )
        else:
            yield from _check_semver_allowed_channels(
                template_names_in_mapping[template["template_name"]], template
            )


def validate_schema_bundle_release_config(bundle: Bundle) -> Iterator[CheckResult]:
    """
    Validate the bundle release config against the json schema
    """
    if not bundle.release_config:
        # missing release config (this is assumed to be ok)
        return
    path_me = os.path.dirname(os.path.abspath(__file__))
    path_schema = os.path.join(path_me, "../schemas/release-config-schema.json")
    with open(path_schema, "r", encoding="utf-8") as file_schema:
        dict_schema = json.load(file_schema)
    # validate the release config against the json schema
    # use iter_errors() to collect and return all validation errors
    validator = Draft202012Validator(dict_schema)
    for ve in sorted(validator.iter_errors(bundle.release_config), key=str):
        yield Fail(
            "Bundle's 'release-config.yaml' contains invalid data "
            f"which does not comply with the schema: {ve.message}"
        )
