from pathlib import Path
from typing import Any

import pytest
from operatorcert.operator_repo import Repo
from operatorcert.operator_repo.checks import Fail, Warn
from operatorcert.static_tests.common.bundle import (
    check_bundle_release_config,
    check_operator_name,
    check_validate_schema_bundle_release_config,
    check_network_policy_presence,
    check_operator_version_directory_name,
)
from tests.utils import bundle_files, create_files


@pytest.mark.parametrize(
    "files, bundle_to_check, expected_results",
    [
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
            ],
            ("hello", "0.0.1"),
            set(),
            id="Names ok",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                    annotations={
                        "operators.operatorframework.io.bundle.package.v1": "foo"
                    },
                ),
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the operator's directory name (hello)",
                ),
                (
                    Fail,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the name defined in the CSV (hello)",
                ),
            },
            id="Wrong annotations.yaml name",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/0.0.1/metadata/annotations.yaml": {
                        "annotations": {}
                    }
                },
            ],
            ("hello", "0.0.1"),
            {
                (Fail, "Bundle does not define the operator name in annotations.yaml"),
            },
            id="Empty annotations.yaml",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                bundle_files(
                    "hello",
                    "0.0.2",
                    annotations={
                        "operators.operatorframework.io.bundle.package.v1": "foo"
                    },
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                    annotations={
                        "operators.operatorframework.io.bundle.package.v1": "foo"
                    },
                ),
            ],
            ("hello", "0.0.3"),
            {
                (
                    Warn,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the operator's directory name (hello)",
                ),
                (
                    Warn,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the name defined in the CSV (hello)",
                ),
                (
                    Warn,
                    "Operator name from annotations.yaml is not consistent"
                    " across bundles: ['foo', 'hello']",
                ),
            },
            id="Wrong annotations.yaml name, inconsistent bundles",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                bundle_files(
                    "hello",
                    "0.0.2",
                    csv={"metadata": {"name": "foo.v0.0.2"}},
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                    csv={"metadata": {"name": "foo.v0.0.3"}},
                ),
            ],
            ("hello", "0.0.3"),
            {
                (
                    Warn,
                    "Operator name from annotations.yaml (hello) does not match"
                    " the name defined in the CSV (foo)",
                ),
                (
                    Warn,
                    "Operator name from the CSV is not consistent across bundles: ['foo', 'hello']",
                ),
            },
            id="Wrong CSV name, inconsistent bundles",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                bundle_files("hello", "0.0.2"),
                bundle_files(
                    "hello",
                    "0.0.3",
                    annotations={
                        "operators.operatorframework.io.bundle.package.v1": "foo"
                    },
                ),
            ],
            ("hello", "0.0.3"),
            {
                (
                    Warn,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the operator's directory name (hello)",
                ),
                (
                    Warn,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the name defined in the CSV (hello)",
                ),
                (
                    Fail,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the name defined in other bundles (hello)",
                ),
            },
            id="Wrong annotations.yaml name, consistent bundles",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                bundle_files("hello", "0.0.2"),
                bundle_files(
                    "hello",
                    "0.0.3",
                    csv={"metadata": {"name": "foo.v0.0.3"}},
                ),
            ],
            ("hello", "0.0.3"),
            {
                (
                    Warn,
                    "Operator name from annotations.yaml (hello) does not match"
                    " the name defined in the CSV (foo)",
                ),
                (
                    Fail,
                    "Operator name from the CSV (foo) does not match the name"
                    " defined in other bundles (hello)",
                ),
            },
            id="Wrong CSV name, consistent bundles",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                    csv={"metadata": {"name": "foo.v0.0.1"}},
                ),
                bundle_files(
                    "hello",
                    "0.0.2",
                    csv={"metadata": {"name": "foo.v0.0.2"}},
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                    csv={"metadata": {"name": "foo.v0.0.3"}},
                ),
            ],
            ("hello", "0.0.3"),
            {
                (
                    Warn,
                    "Operator name from annotations.yaml (hello) does not match"
                    " the name defined in the CSV (foo)",
                ),
            },
            id="Wrong CSV name in all bundles",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                    csv={"metadata": {"name": "hello"}},
                ),
                bundle_files(
                    "hello",
                    "0.0.2",
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                ),
            ],
            ("hello", "0.0.3"),
            set(),
            id="Invalid CSV name in old bundle",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                ),
                bundle_files(
                    "hello",
                    "0.0.2",
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                    csv={"metadata": {"name": "hello"}},
                ),
            ],
            ("hello", "0.0.3"),
            {
                (Fail, "Invalid operator name in CSV for Bundle(hello/0.0.3)"),
            },
            id="Invalid CSV name in new bundle",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                ),
                {"operators/hello/0.0.1/metadata/annotations.yaml": ":invalid"},
                bundle_files(
                    "hello",
                    "0.0.2",
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                ),
            ],
            ("hello", "0.0.3"),
            set(),
            id="Invalid annotations.yaml name in old bundle",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                ),
                bundle_files(
                    "hello",
                    "0.0.2",
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                ),
                {"operators/hello/0.0.3/metadata/annotations.yaml": ":invalid"},
            ],
            ("hello", "0.0.3"),
            {
                (
                    Fail,
                    "Invalid operator name in annotations.yaml for Bundle(hello/0.0.3)",
                ),
            },
            id="Invalid annotations.yaml name in new bundle",
        ),
    ],
    indirect=False,
)
def test_operator_name(
    tmp_path: Path,
    files: list[dict[str, Any]],
    bundle_to_check: tuple[str, str],
    expected_results: set[tuple[type, str]],
) -> None:
    create_files(tmp_path, *files)
    repo = Repo(tmp_path)
    operator_name, bundle_version = bundle_to_check
    operator = repo.operator(operator_name)
    bundle = operator.bundle(bundle_version)
    assert {
        (x.__class__, x.reason) for x in check_operator_name(bundle)
    } == expected_results


@pytest.mark.parametrize(
    "files, bundle_to_check, expected_results",
    [
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
            ],
            ("hello", "0.0.1"),
            set(),
            id="No release config",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                ),
                {"operators/hello/0.0.1/release-config.yaml": {"key": "value"}},
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Bundle's 'release-config.yaml' is used but FBC is not enabled "
                    "for the operator. Update the 'fbc.enabled' field in the ci.yaml file.",
                ),
            },
            id="Release config without FBC",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                ),
                {
                    "operators/hello/0.0.1/release-config.yaml": {
                        "catalog_templates": [
                            {"template_name": "template1.yaml"},
                            {"template_name": "template2.yaml"},
                            {"template_name": "template3.yaml"},
                        ]
                    }
                },
                {
                    "operators/hello/ci.yaml": {
                        "fbc": {
                            "enabled": True,
                            "catalog_mapping": [
                                {
                                    "template_name": "template1.yaml",
                                    "type": "olm.template.basic",
                                }
                            ],
                        }
                    }
                },
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains a catalog template "
                    "'template2.yaml' that is not defined in the ci.yaml file "
                    "under 'catalog_mapping'. Add the template to the 'catalog_mapping.",
                ),
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains a catalog template "
                    "'template3.yaml' that is not defined in the ci.yaml file "
                    "under 'catalog_mapping'. Add the template to the 'catalog_mapping.",
                ),
            },
            id="Missing template in mapping",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                ),
                {
                    "operators/hello/0.0.1/release-config.yaml": {
                        "catalog_templates": [
                            {
                                "template_name": "template1.yaml",
                                "channels": ["Fast", "Candidate", "Stable"],
                            },
                            {
                                "template_name": "template2.yaml",
                                "channels": ["Fast", "Candidate"],
                            },
                            {
                                "template_name": "template3.yaml",
                                "channels": ["Fast", "Custom"],
                            },
                            {"template_name": "template4.yaml", "channels": ["Custom"]},
                        ]
                    }
                },
                {
                    "operators/hello/ci.yaml": {
                        "fbc": {
                            "enabled": True,
                            "catalog_mapping": [
                                {
                                    "template_name": "template1.yaml",
                                    "type": "olm.semver",
                                },
                                {
                                    "template_name": "template2.yaml",
                                    "type": "olm.semver",
                                },
                                {
                                    "template_name": "template3.yaml",
                                    "type": "olm.semver",
                                },
                                {
                                    "template_name": "template4.yaml",
                                    "type": "olm.template.basic",
                                },
                            ],
                        }
                    }
                },
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains a semver catalog template "
                    "'template3.yaml' with invalid channels: ['Fast', 'Custom']. Allowed "
                    "channels are: ['Fast', 'Candidate', 'Stable']. Follow olm "
                    "[documentation](https://olm.operatorframework.io/docs/reference/catalog-templates/#specification) "
                    "to see more details about semver template.",
                ),
            },
            id="Invalid semver channels",
        ),
    ],
    indirect=False,
)
def test_check_bundle_release_config(
    tmp_path: Path,
    files: list[dict[str, Any]],
    bundle_to_check: tuple[str, str],
    expected_results: set[tuple[type, str]],
) -> None:
    create_files(tmp_path, *files)
    repo = Repo(tmp_path)
    operator_name, bundle_version = bundle_to_check
    operator = repo.operator(operator_name)
    bundle = operator.bundle(bundle_version)
    assert {
        (x.__class__, x.reason) for x in check_bundle_release_config(bundle)
    } == expected_results


@pytest.mark.parametrize(
    "files, bundle_to_check, expected_results",
    [
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
            ],
            ("hello", "0.0.1"),
            set(),
            id="pass: no release config",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {"operators/hello/0.0.1/release-config.yaml": {"key": "value"}},
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'catalog_templates' is a required property",
                ),
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains invalid data which does not "
                    "comply with the schema: Additional properties are not allowed ('key' "
                    "was unexpected)",
                ),
            },
            id="fail: release config without catalog_templates",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/0.0.1/release-config.yaml": {
                        "catalog_templates": "hello"
                    }
                },
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'hello' is not of type 'array'",
                ),
            },
            id="fail: release config without proper catalog_templates content",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/0.0.1/release-config.yaml": {
                        "catalog_templates": [{"hello": ""}]
                    }
                },
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'channels' is a required property",
                ),
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'template_name' is a required property",
                ),
            },
            id="fail: release config has catalog_templates no array content",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/0.0.1/release-config.yaml": {
                        "catalog_templates": [{"hello": ""}]
                    }
                },
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'channels' is a required property",
                ),
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'template_name' is a required property",
                ),
            },
            id="fail: release config has catalog_templates missing all required",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/0.0.1/release-config.yaml": {
                        "catalog_templates": [{"channels": ["foo", "bar"]}]
                    }
                },
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'template_name' is a required property",
                ),
            },
            id="fail: release config has catalog_templates missing template_name",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/0.0.1/release-config.yaml": {
                        "catalog_templates": [{"template_name": "foo"}]
                    }
                },
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Bundle's 'release-config.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'channels' is a required property",
                ),
            },
            id="fail: release config has catalog_templates missing channels",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/0.0.1/release-config.yaml": {
                        "catalog_templates": [
                            {"template_name": "foo", "channels": ["foo", "bar"]}
                        ]
                    }
                },
            ],
            ("hello", "0.0.1"),
            set(),
            id="pass: release config has it all!",
        ),
    ],
    indirect=False,
)
def test_check_validate_schema_bundle_release_config(
    tmp_path: Path,
    files: list[dict[str, Any]],
    bundle_to_check: tuple[str, str],
    expected_results: set[tuple[type, str]],
) -> None:
    create_files(tmp_path, *files)
    repo = Repo(tmp_path)
    operator_name, bundle_version = bundle_to_check
    operator = repo.operator(operator_name)
    bundle = operator.bundle(bundle_version)
    assert {
        (x.__class__, x.reason)
        for x in check_validate_schema_bundle_release_config(bundle)
    } == expected_results


@pytest.mark.parametrize(
    "files, bundle_to_check, expected_results",
    [
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
            ],
            ("hello", "0.0.1"),
            set(),
            id="pass: network policy not present",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/0.0.1/manifests/dummy_.k8s.io_v1_networkpolicy.yaml": {
                        "kind": "NetworkPolicy",
                        "apiVersion": "networking.k8s.io/v1",
                    }
                },
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    f"Bundle contains a NetworkPolicy in dummy_.k8s.io_v1_networkpolicy.yaml. "
                    "Network policies are not a supported resource that Operator "
                    "Lifecycle Manager(OLM) can install and manage.",
                ),
            },
            id="fail: A bundle contains a NetworkPolicy",
        ),
    ],
)
def test_check_network_policy_presence(
    tmp_path: Path,
    files: list[dict[str, Any]],
    bundle_to_check: tuple[str, str],
    expected_results: set[tuple[type, str]],
) -> None:
    create_files(tmp_path, *files)
    repo = Repo(tmp_path)
    operator_name, bundle_version = bundle_to_check
    operator = repo.operator(operator_name)
    bundle = operator.bundle(bundle_version)
    assert {
        (x.__class__, x.reason) for x in check_network_policy_presence(bundle)
    } == expected_results


@pytest.mark.parametrize(
    "files, bundle_to_check, expected_results",
    [
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
            ],
            ("hello", "0.0.1"),
            set(),
            id="pass: CSV version matches directory name",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1", csv={"spec": {"version": "0.0.2"}}),
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Bundle directory name 'hello/0.0.1' does not match the expected "
                    "operator CSV version '0.0.2' from "
                    "./operators/hello/0.0.1/manifests/hello.clusterserviceversion.yaml.",
                ),
            },
            id="fail: CSV version does not match directory name",
        ),
    ],
)
def test_check_operator_version_directory_name(
    tmp_path: Path,
    files: list[dict[str, Any]],
    bundle_to_check: tuple[str, str],
    expected_results: set[tuple[type, str]],
) -> None:
    create_files(tmp_path, *files)
    repo = Repo(tmp_path)
    operator_name, bundle_version = bundle_to_check
    operator = repo.operator(operator_name)
    bundle = operator.bundle(bundle_version)
    assert {
        (x.__class__, x.reason) for x in check_operator_version_directory_name(bundle)
    } == expected_results
