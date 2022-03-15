from datetime import timezone
from pathlib import Path
from unittest import mock
from unittest.mock import patch, MagicMock, call
from typing import Dict

import pytest
import yaml
from dateutil.parser import isoparse

import operatorcert

Bundle = Dict[str, Path]


@pytest.fixture
def bundle(tmp_path: Path) -> Bundle:
    tmp_path.joinpath("metadata").mkdir()
    annotations_path = tmp_path.joinpath("metadata", "annotations.yml")

    annotations = {
        "annotations": {
            "operators.operatorframework.io.bundle.package.v1": "foo-operator",
            "com.redhat.openshift.versions": "4.6-4.8",
        }
    }
    with annotations_path.open("w") as fh:
        yaml.safe_dump(annotations, fh)

    tmp_path.joinpath("manifests").mkdir()
    csv_path = tmp_path.joinpath("manifests", "foo-operator.clusterserviceversion.yml")

    csv = {
        "metadata": {
            "annotations": {
                "olm.properties": '[{"type": "olm.maxOpenShiftVersion", "value": "4.7"}]'
            },
        }
    }
    with csv_path.open("w") as fh:
        yaml.safe_dump(csv, fh)

    return {
        "root": tmp_path,
        "annotations": annotations_path,
        "csv": csv_path,
    }


def test_get_csv_content(bundle: Bundle) -> None:
    bundle_root = bundle["root"]
    content = operatorcert.get_csv_content(bundle_root, "foo-operator")
    assert content.get("metadata", {}).get("annotations", {}) == {
        "olm.properties": '[{"type": "olm.maxOpenShiftVersion", "value": "4.7"}]'
    }
    bundle["csv"].unlink()
    with pytest.raises(RuntimeError):
        operatorcert.get_csv_content(bundle_root, "foo-operator")


def test_get_bundle_annotations(bundle: Bundle) -> None:
    bundle_root = bundle["root"]
    assert operatorcert.get_bundle_annotations(bundle_root) == {
        "operators.operatorframework.io.bundle.package.v1": "foo-operator",
        "com.redhat.openshift.versions": "4.6-4.8",
    }
    bundle["annotations"].unlink()
    with pytest.raises(RuntimeError):
        operatorcert.get_bundle_annotations(bundle_root)


@patch("operatorcert.pyxis.get")
def test_get_supported_indices(mock_get: MagicMock) -> None:
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = {"data": ["foo", "bar"]}
    mock_get.return_value = mock_rsp

    result = operatorcert.get_supported_indices(
        "https://foo.bar", "4.6-4.8", "certified-operators"
    )
    assert result == ["foo", "bar"]


@patch("operatorcert.datetime")
@patch("operatorcert.get_supported_indices")
def test_ocp_version_info(
    mock_indices: MagicMock, mock_datetime: MagicMock, bundle: Bundle
) -> None:
    timestamp = "2022-01-01T00:00:00.000000+00:00"
    mock_datetime.now.return_value = isoparse(timestamp).astimezone(timezone.utc)
    organization = "certified-operators"
    bundle_root = bundle["root"]

    # Happy path
    mock_indices.return_value = [{"ocp_version": "4.7", "path": "quay.io/foo:4.7"}]
    info = operatorcert.ocp_version_info(bundle_root, "", organization)
    assert info == {
        "versions_annotation": "4.6-4.8",
        "indices": mock_indices.return_value,
        "max_version_index": mock_indices.return_value[0],
    }

    # No supported indices found
    mock_indices.return_value = []
    with pytest.raises(ValueError):
        operatorcert.ocp_version_info(bundle_root, "", organization)

    # Index EOL reached
    mock_indices.return_value = [
        {
            "ocp_version": "4.7",
            "path": "quay.io/foo:4.7",
            "end_of_life": timestamp,
        }
    ]
    with pytest.raises(ValueError) as err_info:
        operatorcert.ocp_version_info(bundle_root, "", organization)
    assert str(err_info.value) == "OpenShift 4.7 has reached its end of life"

    # Missing version range annotation
    annotations = {
        "annotations": {
            "operators.operatorframework.io.bundle.package.v1": "foo-operator",
        }
    }
    with bundle["annotations"].open("w") as fh:
        yaml.safe_dump(annotations, fh)

    with pytest.raises(ValueError) as err_info:
        operatorcert.ocp_version_info(bundle_root, "", organization)
    assert (
        str(err_info.value) == "'com.redhat.openshift.versions' annotation not defined"
    )

    # Missing package name annotation
    annotations["annotations"] = {"com.redhat.openshift.versions": "4.6-4.8"}
    with bundle["annotations"].open("w") as fh:
        yaml.safe_dump(annotations, fh)

    with pytest.raises(ValueError) as err_info:
        operatorcert.ocp_version_info(bundle_root, "", organization)
    assert (
        str(err_info.value)
        == "'operators.operatorframework.io.bundle.package.v1' annotation not defined"
    )


def test_get_repo_and_org_from_github_url():
    # test http and ssh
    for url in [
        "git@github.com:redhat-openshift-ecosystem/operator-pipelines.git",
        "https://github.com/redhat-openshift-ecosystem/operator-pipelines.git",
    ]:
        org, repo = operatorcert.get_repo_and_org_from_github_url(url)
        assert org == "redhat-openshift-ecosystem"
        assert repo == "operator-pipelines"

    # wrong schema
    with pytest.raises(ValueError):
        operatorcert.get_repo_and_org_from_github_url(
            "github.com/redhat-openshift-ecosystem/operator-pipelines/something"
        )

    # wrong amount of url segments
    with pytest.raises(ValueError):
        operatorcert.get_repo_and_org_from_github_url(
            "git@github.com:redhat-openshift-ecosystem/operator-pipelines/something.git"
        )


@patch("operatorcert.github.get")
def test_get_files_added_in_pr(mock_get: MagicMock):
    mock_get.return_value = {
        "irrelevant_key": "abc",
        "files": [
            {"filename": "first", "status": "added"},
            {"filename": "second", "status": "added"},
        ],
    }
    files = operatorcert.get_files_added_in_pr(
        "rh", "operator-repo", "main", "user:fixup"
    )
    mock_get.assert_called_with(
        "https://api.github.com/repos/rh/operator-repo/compare/main...user:fixup",
        auth_required=False,
    )
    assert files == ["first", "second"]


@patch("operatorcert.github.get")
def test_get_files_added_in_pr_changed_files(mock_get: MagicMock):
    mock_get.return_value = {
        "irrelevant_key": "abc",
        "files": [
            {"filename": "first", "status": "deleted"},
            {"filename": "second", "status": "changed"},
        ],
    }
    with pytest.raises(RuntimeError):
        operatorcert.get_files_added_in_pr("rh", "operator-repo", "main", "user:fixup")
    mock_get.assert_called_with(
        "https://api.github.com/repos/rh/operator-repo/compare/main...user:fixup",
        auth_required=False,
    )


@patch("operatorcert.github.get")
def test_get_files_added_in_pr_changed_ci_yaml(mock_get: MagicMock):
    mock_get.return_value = {
        "irrelevant_key": "abc",
        "files": [
            {"filename": "ci.yaml", "status": "changed"},
        ],
    }
    files = operatorcert.get_files_added_in_pr(
        "rh", "operator-repo", "main", "user:fixup"
    )

    mock_get.assert_called_with(
        "https://api.github.com/repos/rh/operator-repo/compare/main...user:fixup",
        auth_required=False,
    )

    assert files == ["ci.yaml"]


@pytest.mark.parametrize(
    "wrong_change",
    [
        # no wrong change, happy path
        "",
        # wrong repository
        "other-repository/operators/sample-operator/0.1.0/1.txt",
        # wrong operator name
        "sample-repository/operators/other-operator/0.1.0/1.txt",
        # wrong version
        "sample-repository/operators/sample-operator/0.1.1/1.txt",
        # change other than ci.yaml in the operator directory level
        "sample-repository/operators/sample-operator/1.txt",
    ],
)
def test_verify_changed_files_location(wrong_change: str):
    changed_files = [
        "operators/sample-operator/0.1.0/1.txt",
        "operators/sample-operator/0.1.0/directory/2.txt",
        "operators/sample-operator/ci.yaml",
    ]
    operator_name = "sample-operator"
    bundle_version = "0.1.0"

    # sad paths
    if wrong_change:
        with pytest.raises(RuntimeError):
            operatorcert.verify_changed_files_location(
                changed_files + [wrong_change],
                operator_name,
                bundle_version,
            )
    # happy path
    else:
        operatorcert.verify_changed_files_location(
            changed_files, operator_name, bundle_version
        )


@pytest.mark.parametrize(
    "pr_title, is_valid, name, version",
    [
        ("operator operator-test123 (1.0.1)", True, "operator-test123", "1.0.1"),
        ("operator OPERATOR (1.0.1-ok)", True, "OPERATOR", "1.0.1-ok"),
        ("operator operator-test123 (1.0.1) aa", False, "", ""),
        ("operator  (1.0.1)", False, "", ""),
        ("operator-test123 (1.0.1)", False, "", ""),
        ("operator-test123 (1.0.1)", False, "", ""),
        ("operator oper@tor-test123 (1.0.1)", False, "", ""),
        ("operator operator-test123 (1)", True, "operator-test123", "1"),
    ],
)
def test_parse_pr_title(pr_title: str, is_valid: bool, name: str, version: str):
    if is_valid:
        res_name, res_version = operatorcert.parse_pr_title(pr_title)
        assert res_name == name
        assert res_version == version
    else:
        with pytest.raises(ValueError):
            operatorcert.parse_pr_title(pr_title)


@patch("operatorcert.github.get")
def test_verify_pr_uniqueness(mock_get: MagicMock):
    base_pr_url = "https://github.com/user/repo/pulls/1"
    pr_rsp = [
        # At first call get return:
        [
            {"title": "operator first (1.2.3)", "html_url": base_pr_url},
            {
                "title": "operator second (1.2.3)",
                "html_url": base_pr_url.replace("1", "2"),
            },
            {
                "title": "operator third (1.2.3)",
                "html_url": base_pr_url.replace("1", "3"),
            },
            {
                "title": "title not conforming regex- should not throw error",
                "html_url": base_pr_url.replace("1", "4"),
            },
        ],
        # At second call return:
        [
            {
                "title": "operator fourth (1.2.3)",
                "html_url": base_pr_url.replace("1", "5"),
            }
        ],
    ]

    mock_get.side_effect = pr_rsp

    available_repositories = ["org1/repo_a", "org2/repo_b"]
    base_pr_bundle_name = "first"
    operatorcert.verify_pr_uniqueness(
        available_repositories, base_pr_url, base_pr_bundle_name
    )

    # For second call return PR title with the same operator name, but other version
    pr_rsp[1].append(
        {"title": "operator first (1.2.4)", "html_url": base_pr_url.replace("1", "5")}
    )
    mock_get.side_effect = pr_rsp

    assert mock_get.call_args_list == [
        call("https://api.github.com/repos/org1/repo_a/pulls", auth_required=False),
        call("https://api.github.com/repos/org2/repo_b/pulls", auth_required=False),
    ]

    with pytest.raises(RuntimeError):
        operatorcert.verify_pr_uniqueness(
            available_repositories, base_pr_url, base_pr_bundle_name
        )


def test_validate_user():
    contacts = ["some_user", "some_other_user"]

    operatorcert.validate_user("some_user", contacts)

    with pytest.raises(Exception):
        operatorcert.validate_user("one_without_permissions", contacts)


@patch("operatorcert.pyxis.get")
def test_download_test_results(mock_get: MagicMock):
    # Arrange
    args = MagicMock()
    args.pyxis_url = "https://pyxis.engineering.redhat.com"
    args.cert_project_id = "123456"
    args.certification_hash = "123456abc"
    args.operator_name = "foo"
    args.operator_package_version = "12345"
    args.cert_path = "/non/existing/path.crt"
    args.key_path = "/non/existing/path.key"
    test_results_url = (
        "https://pyxis.engineering.redhat.com/v1/projects/certification/id/123456/test-results?filter"
        "=certification_hash=='123456abc';version=='12345';operator_package_name=='foo'&sort_by"
        "=creation_date[desc]&page_size=1"
    )

    mock_rsp = MagicMock()
    mock_open = mock.mock_open()

    # No resource got
    mock_rsp.json.return_value = {"data": []}
    mock_get.return_value = mock_rsp
    # Act
    result_id = operatorcert.download_test_results(args)
    # Assert
    assert result_id is None

    # Happy path- there are resources (test results)
    mock_rsp.json.return_value = {
        "data": [
            {
                "_id": "1234",
                "results": {"a": "ok"},
                "passed": True,
                "test_library": {},
            }
        ]
    }
    mock_get.return_value = mock_rsp
    # Act
    with mock.patch("builtins.open", mock_open):
        result_id = operatorcert.download_test_results(args)
    # Assert
    assert result_id == "1234"
    mock_get.assert_called_with(test_results_url)
    mock_open.assert_called_with("test_results.json", "w")
