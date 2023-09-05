import re
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from operator_repo import Repo
from operator_repo.checks import CheckResult, Fail, Warn
from operatorcert.static_tests.community.bundle import (
    check_osdk_bundle_validate,
    check_required_fields,
)
from tests.utils import bundle_files, create_files, merge


@pytest.mark.parametrize(
    "osdk_output, expected",
    [
        (
            '{"passed": false, "outputs":'
            '[{"type": "error", "message": "foo"}, {"type": "warning", "message": "bar"}]}',
            {Fail("foo"), Warn("bar")},
        ),
        (
            '{"passed": true, "outputs": null}',
            set(),
        ),
    ],
    indirect=False,
    ids=[
        "A warning and an error",
        "No warnings or errors",
    ],
)
@patch("subprocess.run")
def test_osdk_bundle_validate(
    mock_run: MagicMock, osdk_output: str, expected: set[CheckResult], tmp_path: Path
) -> None:
    create_files(tmp_path, bundle_files("test-operator", "0.0.1"))
    repo = Repo(tmp_path)
    bundle = repo.operator("test-operator").bundle("0.0.1")
    process_mock = MagicMock()
    process_mock.stdout = osdk_output
    mock_run.return_value = process_mock
    assert set(check_osdk_bundle_validate(bundle)) == expected


def _make_nested_dict(path: str, value: Any) -> Dict[str, Any]:
    """
    _make_nested_dict("foo.bar", "baz") -> {"foo": {"bar": "baz"}}
    """
    result: Dict[str, Any] = {}
    current = result
    keys = path.split(".")
    for key in keys[:-1]:
        current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    return result


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {
            "metadata.annotations.capabilities": ("", "failure", "invalid"),
            "metadata.annotations.categories": ("", "warning", "invalid"),
            "metadata.annotations.containerImage": ("", "failure", "invalid"),
            "metadata.annotations.createdAt": ("", "failure", "invalid"),
            "metadata.annotations.repository": ("", "warning", "invalid"),
            "metadata.annotations.support": ("", "failure", "invalid"),
            "metadata.annotations.alm-examples": ("", "failure", "invalid"),
            "metadata.annotations.description": ("", "warning", "invalid"),
            "spec.displayName": ("", "failure", "invalid"),
            "spec.description": ("", "failure", "invalid"),
            "spec.icon": ("", "failure", "invalid"),
            "spec.version": ("", "failure", "invalid"),
            "spec.maintainers": ("", "failure", "invalid"),
            "spec.provider.name": ("", "failure", "invalid"),
            "spec.links": ("", "failure", "invalid"),
            "spec.keywords": ("", "failure", "invalid"),
        },
        {
            "metadata.annotations.capabilities": ("Basic Install", "warning", "valid"),
            "metadata.annotations.categories": ("Storage,Security", "warning", "valid"),
            "metadata.annotations.containerImage": (
                "example.com/foo/bar:tag",
                "failure",
                "valid",
            ),
            "metadata.annotations.createdAt": (
                "2023-08-15T12:00:00Z",
                "failure",
                "valid",
            ),
            "metadata.annotations.repository": (
                "https://example.com/foo/bar.git",
                "warning",
                "valid",
            ),
            "metadata.annotations.support": (
                "Accusamus quidem quam enim dolor.",
                "failure",
                "valid",
            ),
            "metadata.annotations.alm-examples": (
                "Accusamus quidem quam enim dolor.",
                "failure",
                "valid",
            ),
            "metadata.annotations.description": (
                "Accusamus quidem quam enim dolor.",
                "warning",
                "valid",
            ),
            "spec.displayName": (
                "Accusamus quidem quam enim dolor.",
                "failure",
                "valid",
            ),
            "spec.description": (
                "Accusamus quidem quam enim dolor.",
                "failure",
                "valid",
            ),
            "spec.icon": (
                [{"base64data": "Zm9v", "mediatype": "image/svg+xml"}],
                "failure",
                "valid",
            ),
            "spec.version": ("0.0.1", "failure", "valid"),
            "spec.maintainers": (
                [{"name": "John Doe", "email": "jdoe@example.com"}],
                "failure",
                "valid",
            ),
            "spec.provider.name": ({"name": "ACME Corp."}, "failure", "valid"),
            "spec.links": (
                [{"name": "example", "url": "https://example.com/"}],
                "failure",
                "valid",
            ),
            "spec.keywords": (["foo", "bar"], "failure", "valid"),
        },
    ],
    indirect=False,
    ids=[
        "All missing",
        "All invalid",
        "All valid",
    ],
)
def test_required_fields(
    tmp_path: Path, fields: dict[str, tuple[Any, str, str]]
) -> None:
    csv_fields: Dict[str, Any] = {}
    for path, (value, _, _) in fields.items():
        merge(csv_fields, _make_nested_dict(path, value))
    create_files(tmp_path, bundle_files("test-operator", "0.0.1", csv=csv_fields))
    repo = Repo(tmp_path)
    bundle = repo.operator("test-operator").bundle("0.0.1")

    re_missing = re.compile(r"CSV does not define (.+)")
    re_invalid = re.compile(r"CSV contains an invalid value for (.+)")

    collected_results = {}

    for result in check_required_fields(bundle):
        match_missing = re_missing.match(result.reason)
        if match_missing:
            collected_results[match_missing.group(1)] = (result.kind, "missing")
            continue
        match_invalid = re_invalid.match(result.reason)
        if match_invalid:
            collected_results[match_invalid.group(1)] = (result.kind, "invalid")

    expected_problems = {k for k, (_, __, t) in fields.items() if t != "valid"}
    expected_successes = set(fields.keys()) - expected_problems
    assert {k: v for k, v in collected_results.items() if k in expected_problems} == {
        k: (s, t) for k, (_, s, t) in fields.items() if t != "valid"
    }
    assert all(
        t == "missing" for k, (_, t) in collected_results.items() if k not in fields
    )
    assert expected_successes.intersection(collected_results.keys()) == set()
