import json
import re
import subprocess
from collections.abc import Iterator

from operator_repo import Bundle
from operator_repo.checks import CheckResult, Fail, Warn
from operator_repo.utils import lookup_dict

from .validations import (
    validate_capabilities,
    validate_categories,
    validate_icon,
    validate_links,
    validate_list_of_strings,
    validate_maintainers,
    validate_semver,
    validate_timestamp,
)


def check_osdk_bundle_validate(bundle: Bundle) -> Iterator[CheckResult]:
    """Run `operator-sdk bundle validate` using operatorhub settings"""
    cmd = [
        "operator-sdk",
        "bundle",
        "validate",
        "-o",
        "json-alpha1",
        bundle.root,
        "--select-optional",
        "name=operatorhub",
    ]
    sdk_result = json.loads(
        subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False
        ).stdout
    )
    for output in sdk_result.get("outputs", []):
        output_type = output.get("type")
        output_message = output.get("message", "")
        if output_type == "error":
            yield Fail(output_message)
        else:
            yield Warn(output_message)


def check_required_fields(bundle: Bundle) -> Iterator[CheckResult]:
    """Ensure the CSV contains all required fields"""
    # From https://github.com/operator-framework/community-operators/blob/master/docs/packaging-required-fields.md#required-fields-for-operatorhub
    required_fields = [
        # Field, validation, fatal
        ("metadata.annotations.capabilities", validate_capabilities, True),
        ("metadata.annotations.categories", validate_categories, False),
        (
            "metadata.annotations.containerImage",
            re.compile(r"[^/]+/[^/]+/[^/:]+:.+"),
            True,
        ),
        ("metadata.annotations.createdAt", validate_timestamp, True),
        ("metadata.annotations.repository", re.compile(r"https?://.+"), False),
        ("metadata.annotations.support", re.compile(r".{3,}", re.DOTALL), True),
        ("metadata.annotations.alm-examples", re.compile(r".{30,}", re.DOTALL), True),
        ("metadata.annotations.description", re.compile(r".{10,}", re.DOTALL), False),
        ("spec.displayName", re.compile(r".{3,50}"), True),
        ("spec.description", re.compile(r".{20,}", re.DOTALL), True),
        ("spec.icon", validate_icon, True),
        ("spec.version", validate_semver, True),
        ("spec.maintainers", validate_maintainers, True),
        ("spec.provider.name", re.compile(r".{3,}"), True),
        ("spec.links", validate_links, True),
        ("spec.keywords", validate_list_of_strings, True),
    ]

    csv = bundle.csv
    for field, validation, fatal in required_fields:
        value = lookup_dict(csv, field)
        if value is None:
            success = False
            message = f"CSV does not define {field}"
        else:
            success = True
            if isinstance(validation, re.Pattern):
                success = bool(validation.match(str(value)))
            elif callable(validation):
                success = validation(value)
            message = f"CSV contains an invalid value for {field}"
        if success:
            continue
        yield Fail(message) if fatal else Warn(message)
