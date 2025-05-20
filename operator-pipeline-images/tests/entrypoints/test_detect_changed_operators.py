import pathlib
import tarfile
from dataclasses import dataclass
from typing import Any, Dict
from unittest.mock import MagicMock, mock_open, patch

import pytest
from git.repo import Repo as GitRepo
from operatorcert.entrypoints import detect_changed_operators
from operatorcert.operator_repo import Repo
from operatorcert.parsed_file import (
    AffectedBundleCollection,
    AffectedCatalogCollection,
    AffectedCatalogOperatorCollection,
    AffectedOperatorCollection,
    ParserResults,
    ParserRules,
    ValidationError,
)


@pytest.mark.parametrize(
    # The tar file contains an operator repository with the following
    # commits (last to first):
    # 8a40093 Add catalog template to operator-e2e
    # 244d87b Add invalid catalog file
    # 1ca2aa1 Delete 4.15 catalog
    # 8500957 Remove operator-2 from v4.15
    # ff7cdcd Update operator-1 in 4.15 catalog
    # 4db21de Add operator-2 to 4.15 catalog
    # c8d3509 Add 4.15 catalog with operator-1
    # 2e9eae2 Remove operator-clone-e2e
    # a5501e2 Add ci.yaml to operator-clone-e2e
    # 2c06647 Remove extra files
    # 4143429 Remove operator-e2e/0.0.101
    # 2d55a2e Add extra files
    # 9f7ef05 Modify operator-e2e/0.0.101
    # ad1e1de Modify operator-clone-e2e/0.0.100
    # 6626c9a Add operator-clone-e2e/0.0.100
    # 32e0f85 Add operator-e2e/0.0.101
    # 6a75661 Add operator-e2e/0.0.100
    # db1a066 Empty repo
    "head_commit, base_commit, expected",
    [
        pytest.param(
            "6a75661",
            # Add operator-e2e/0.0.100
            # Empty repo
            "db1a066",
            {
                "affected_operators": ["operator-e2e"],
                "added_or_modified_operators": ["operator-e2e"],
                "added_operators": ["operator-e2e"],
                "affected_bundles": ["operator-e2e/0.0.100"],
                "added_bundles": ["operator-e2e/0.0.100"],
                "added_or_modified_bundles": ["operator-e2e/0.0.100"],
            },
            id="Add new bundle for new operator",
        ),
        pytest.param(
            "32e0f85",
            # Add operator-e2e/0.0.101
            # Add operator-e2e/0.0.100
            "6a75661",
            {
                "affected_operators": ["operator-e2e"],
                "added_or_modified_operators": ["operator-e2e"],
                "modified_operators": ["operator-e2e"],
                "affected_bundles": ["operator-e2e/0.0.101"],
                "added_bundles": ["operator-e2e/0.0.101"],
                "added_or_modified_bundles": ["operator-e2e/0.0.101"],
            },
            id="Add new bundle for existing operator",
        ),
        pytest.param(
            "6626c9a",
            # Add operator-clone-e2e/0.0.100
            # Add operator-e2e/0.0.101
            # Add operator-e2e/0.0.100
            "6a75661",
            {
                "affected_operators": ["operator-e2e", "operator-clone-e2e"],
                "added_or_modified_operators": ["operator-e2e", "operator-clone-e2e"],
                "added_operators": ["operator-clone-e2e"],
                "modified_operators": ["operator-e2e"],
                "affected_bundles": [
                    "operator-e2e/0.0.101",
                    "operator-clone-e2e/0.0.100",
                ],
                "added_bundles": ["operator-e2e/0.0.101", "operator-clone-e2e/0.0.100"],
                "added_or_modified_bundles": [
                    "operator-e2e/0.0.101",
                    "operator-clone-e2e/0.0.100",
                ],
            },
            id="Add bundles for multiple operators",
        ),
        pytest.param(
            "2d55a2e",
            # Add extra files
            # Modify operator-e2e/0.0.101
            # Modify operator-clone-e2e/0.0.100
            # Add operator-clone-e2e/0.0.100
            "6626c9a",
            {
                "extra_files": ["empty.txt", "operators/empty.txt"],
                "affected_operators": ["operator-e2e", "operator-clone-e2e"],
                "added_or_modified_operators": ["operator-e2e", "operator-clone-e2e"],
                "modified_operators": ["operator-e2e", "operator-clone-e2e"],
                "affected_bundles": [
                    "operator-e2e/0.0.101",
                    "operator-clone-e2e/0.0.100",
                ],
                "modified_bundles": [
                    "operator-e2e/0.0.101",
                    "operator-clone-e2e/0.0.100",
                ],
                "added_or_modified_bundles": [
                    "operator-e2e/0.0.101",
                    "operator-clone-e2e/0.0.100",
                ],
            },
            id="Modify bundles for multiple operators and add extra files",
        ),
        pytest.param(
            "2c06647",
            # Remove extra files
            # Remove operator-e2e/0.0.101
            # Add extra files
            "2d55a2e",
            {
                "extra_files": ["empty.txt", "operators/empty.txt"],
                "affected_operators": ["operator-e2e"],
                "added_or_modified_operators": ["operator-e2e"],
                "modified_operators": ["operator-e2e"],
                "affected_bundles": ["operator-e2e/0.0.101"],
                "deleted_bundles": ["operator-e2e/0.0.101"],
            },
            id="Delete a bundle and remove extra files",
        ),
        pytest.param(
            "a5501e2",
            # Add ci.yaml to operator-clone-e2e
            # Remove extra files
            "2c06647",
            {
                "affected_operators": ["operator-clone-e2e"],
                "added_or_modified_operators": ["operator-clone-e2e"],
                "modified_operators": ["operator-clone-e2e"],
            },
            id="Add ci.yaml to an operator",
        ),
        pytest.param(
            "2e9eae2",
            # Remove operator-clone-e2e
            # Add ci.yaml to operator-clone-e2e
            "a5501e2",
            {
                "affected_operators": ["operator-clone-e2e"],
                "deleted_operators": ["operator-clone-e2e"],
                "affected_bundles": ["operator-clone-e2e/0.0.100"],
                "deleted_bundles": ["operator-clone-e2e/0.0.100"],
            },
            id="Delete an operator",
        ),
        pytest.param(
            "c8d3509f",
            # Add v4.15/operator-1
            "2e9eae2",
            {
                "affected_catalog_operators": ["v4.15/operator-1"],
                "added_catalog_operators": ["v4.15/operator-1"],
                "affected_catalogs": ["v4.15"],
                "added_catalogs": ["v4.15"],
                "added_or_modified_catalogs": ["v4.15"],
                "catalogs_with_added_or_modified_operators": ["v4.15"],
            },
            id="Add new catalog with new operator",
        ),
        pytest.param(
            "4db21de1",
            # Add v4.15/operator-2
            "c8d3509f",
            {
                "affected_catalog_operators": ["v4.15/operator-2"],
                "added_catalog_operators": ["v4.15/operator-2"],
                "affected_catalogs": ["v4.15"],
                "modified_catalogs": ["v4.15"],
                "added_or_modified_catalogs": ["v4.15"],
                "catalogs_with_added_or_modified_operators": ["v4.15"],
            },
            id="Add new operator to existing catalog",
        ),
        pytest.param(
            "ff7cdcd6",
            # Modify v4.15/operator-1
            "4db21de1",
            {
                "affected_catalog_operators": ["v4.15/operator-1"],
                "modified_catalog_operators": ["v4.15/operator-1"],
                "affected_catalogs": ["v4.15"],
                "modified_catalogs": ["v4.15"],
                "added_or_modified_catalogs": ["v4.15"],
                "catalogs_with_added_or_modified_operators": ["v4.15"],
            },
            id="Modify operator in existing catalog",
        ),
        pytest.param(
            "85009570",
            # Delete v4.15/operator-2
            "ff7cdcd6",
            {
                "affected_catalog_operators": ["v4.15/operator-2"],
                "deleted_catalog_operators": ["v4.15/operator-2"],
                "affected_catalogs": ["v4.15"],
                "modified_catalogs": ["v4.15"],
                "added_or_modified_catalogs": ["v4.15"],
            },
            id="Delete operator in existing catalog",
        ),
        pytest.param(
            "1ca2aa12",
            # Delete v4.15 catalog
            "85009570",
            {
                "affected_catalog_operators": ["v4.15/operator-1"],
                "deleted_catalog_operators": ["v4.15/operator-1"],
                "affected_catalogs": ["v4.15"],
                "deleted_catalogs": ["v4.15"],
            },
            id="Delete catalog",
        ),
        pytest.param(
            "ff7cdcd",
            # Modify v4.15/operator-1
            # Add v4.15/operator-2
            "c8d3509",
            {
                "affected_catalogs": ["v4.15"],
                "modified_catalogs": ["v4.15"],
                "added_or_modified_catalogs": ["v4.15"],
                "catalogs_with_added_or_modified_operators": ["v4.15"],
                "affected_catalog_operators": ["v4.15/operator-1", "v4.15/operator-2"],
                "added_catalog_operators": ["v4.15/operator-2"],
                "modified_catalog_operators": ["v4.15/operator-1"],
            },
            id="Modify operator in existing catalog and add new operator",
        ),
        pytest.param(
            "244d87b",
            # Delete v4.15 catalog
            # Add invalid catalog file
            "1ca2aa12",
            {
                "extra_files": ["catalogs/v4.11-invalid/foo.json"],
            },
            id="Add invalid catalog file",
        ),
        pytest.param(
            "8a40093eff",
            # Add catalog template to operator-e2e
            # Add invalid catalog file
            "244d87b92",
            {
                "affected_operators": ["operator-e2e"],
                "added_or_modified_operators": ["operator-e2e"],
                "modified_operators": ["operator-e2e"],
            },
            id="Add catalog template to operator-e2e",
        ),
    ],
    indirect=False,
)
@patch("operatorcert.entrypoints.detect_changed_operators.ParserResults.enrich_result")
@patch("operatorcert.entrypoints.detect_changed_operators.github_pr_affected_files")
def test_detect_changes(
    mock_affected_files: MagicMock,
    mock_enrich_result: MagicMock,
    tmp_path: pathlib.Path,
    head_commit: str,
    base_commit: str,
    expected: Any,
) -> None:
    data_dir = pathlib.Path(__file__).parent.parent.resolve() / "data"
    tar = tarfile.open(str(data_dir / "test-repo.tar"))
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    before_dir.mkdir()
    after_dir.mkdir()
    tar.extractall(before_dir)
    tar.extractall(after_dir)
    before_git = GitRepo(before_dir)
    after_git = GitRepo(after_dir)
    before_git.head.reset(base_commit, index=True, working_tree=True)
    after_git.head.reset(head_commit, index=True, working_tree=True)

    affected_files = {
        y
        for x in after_git.head.commit.diff(base_commit)
        for y in (x.a_path, x.b_path)
        if y
        is not None  # According to the GitPython docs, a_path and b_path can be None
    }
    mock_affected_files.return_value = affected_files

    result = detect_changed_operators.detect_changes(
        Repo(after_dir),
        Repo(before_dir),
        "https://example.com/foo/bar/pull/1",
    )

    default_expected: dict[str, Any] = {
        "extra_files": [],
        "affected_operators": [],
        "added_or_modified_operators": [],
        "added_operators": [],
        "modified_operators": [],
        "deleted_operators": [],
        "affected_bundles": [],
        "added_or_modified_bundles": [],
        "added_bundles": [],
        "modified_bundles": [],
        "deleted_bundles": [],
        "affected_catalog_operators": [],
        "added_catalog_operators": [],
        "modified_catalog_operators": [],
        "deleted_catalog_operators": [],
        "affected_catalogs": [],
        "added_catalogs": [],
        "modified_catalogs": [],
        "added_or_modified_catalogs": [],
        "deleted_catalogs": [],
        "catalogs_with_added_or_modified_operators": [],
    }
    expected = {**default_expected, **expected}

    result_dict = result.to_dict()

    for key in set(result_dict.keys()) | set(expected.keys()):
        assert sorted(result_dict[key]) == sorted(
            expected[key]
        ), f"Invalid value for {key}: expected {expected[key]} but {result_dict[key]} was returned"


@patch("operatorcert.entrypoints.detect_changed_operators.ParserRules")
@patch("operatorcert.entrypoints.detect_changed_operators.OperatorRepo")
@patch("operatorcert.entrypoints.detect_changed_operators.detect_changes")
@patch("operatorcert.entrypoints.detect_changed_operators.setup_logger")
def test_detect_changed_operators_main(
    mock_logger: MagicMock,
    mock_detect: MagicMock,
    mock_repo: MagicMock,
    mock_validate: MagicMock,
    capsys: Any,
    tmpdir: Any,
) -> None:
    args = [
        "detect_changed_operators",
        "--repo-path=/tmp/repo",
        "--base-repo-path=/tmp/base-repo",
        "--pr-url=https://example.com/foo/bar/pull/1",
    ]
    parsed_result = MagicMock()
    parsed_result.to_dict.return_value = {}
    mock_detect.return_value = parsed_result
    repo_head = MagicMock()
    repo_base = MagicMock()
    mock_repo.side_effect = [repo_head, repo_base, repo_head, repo_base]
    with patch("sys.argv", args):
        detect_changed_operators.main()
    mock_detect.assert_called_once_with(
        repo_head,
        repo_base,
        "https://example.com/foo/bar/pull/1",
    )
    assert capsys.readouterr().out.strip() == "{}"
    mock_logger.assert_called_once_with(level="INFO")
    mock_validate.assert_called_once()
    parsed_result.to_dict.assert_called_once()

    mock_logger.reset_mock()
    mock_detect.reset_mock()

    out_file = tmpdir / "out.json"
    out_file_name = str(out_file)
    args = [
        "detect_changed_operators",
        "--repo-path=/tmp/repo",
        "--base-repo-path=/tmp/base-repo",
        "--pr-url=https://example.com/foo/bar/pull/1",
        f"--output-file={out_file_name}",
        "--verbose",
    ]
    mock_detect.return_value = parsed_result
    with patch("sys.argv", args):
        detect_changed_operators.main()
    mock_detect.assert_called_once_with(
        repo_head,
        repo_base,
        "https://example.com/foo/bar/pull/1",
    )
    assert out_file.read().strip() == "{}"
    mock_logger.assert_called_once_with(level="DEBUG")


@pytest.fixture
def mock_pull() -> MagicMock:
    @dataclass
    class FileMock:
        filename: str

    result = MagicMock()
    result.get_files = MagicMock(
        return_value=[FileMock("foo.txt"), FileMock("bar.yaml")]
    )
    return result


@patch("operatorcert.entrypoints.detect_changed_operators.Auth.Token")
@patch("operatorcert.entrypoints.detect_changed_operators.Github")
def test_github_pr_affected_files(
    mock_github: MagicMock,
    mock_token: MagicMock,
    mock_pull: MagicMock,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    mock_token.return_value = "auth_result"

    mock_repo = MagicMock()
    mock_repo.get_pull = MagicMock(return_value=mock_pull)
    mock_gh = MagicMock()
    mock_gh.get_repo = MagicMock(return_value=mock_repo)
    mock_github.return_value = mock_gh

    assert detect_changed_operators.github_pr_affected_files(
        "https://example.com/foo/bar/pull/123"
    ) == {
        "foo.txt",
        "bar.yaml",
    }
    mock_github.assert_called_once_with(auth="auth_result")
    mock_gh.get_repo.assert_called_once_with("foo/bar")
    mock_repo.get_pull.assert_called_once_with(123)
    mock_pull.get_files.assert_called_once()


@patch("operatorcert.entrypoints.detect_changed_operators.Github")
def test_github_pr_affected_files_no_token(
    mock_github: MagicMock,
    mock_pull: MagicMock,
    monkeypatch: Any,
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    mock_repo = MagicMock()
    mock_repo.get_pull = MagicMock(return_value=mock_pull)
    mock_gh = MagicMock()
    mock_gh.get_repo = MagicMock(return_value=mock_repo)
    mock_github.return_value = mock_gh

    assert detect_changed_operators.github_pr_affected_files(
        "https://example.com/foo/bar/pull/123"
    ) == {
        "foo.txt",
        "bar.yaml",
    }
    mock_github.assert_called_once_with()
    mock_gh.get_repo.assert_called_once_with("foo/bar")
    mock_repo.get_pull.assert_called_once_with(123)
    mock_pull.get_files.assert_called_once()


def test_github_pr_affected_files_invalid_url(
    monkeypatch: Any,
) -> None:
    with pytest.raises(ValueError):
        detect_changed_operators.github_pr_affected_files(
            "http://example.com/invalid/url"
        )


@pytest.mark.parametrize(
    "result, valid, message",
    [
        pytest.param(
            {
                "extra_files": ["empty.txt", "operators/empty.txt"],
            },
            False,
            "The PR affects non-operator files: ['empty.txt', 'operators/empty.txt']",
            id="Extra files",
        ),
        pytest.param(
            {
                "extra_files": [],
                "added_operators": ["operator-e2e", "operator-clone-e2e"],
            },
            True,
            None,
            id="Multiple operators - no bundle change",
        ),
        pytest.param(
            {
                "extra_files": [],
                "added_operators": ["operator-e2e", "operator-clone-e2e"],
                "added_bundles": [("operator-e2e", "0.0.101")],
            },
            False,
            "The PR affects more than one operator: ['operator-clone-e2e', 'operator-e2e']",
            id="Multiple operators - with bundle change",
        ),
        pytest.param(
            {
                "modified_bundles": [("operator-e2e", "0.0.101")],
            },
            False,
            "The PR modifies existing bundles: [('operator-e2e', '0.0.101')]",
            id="Modified bundles",
        ),
        pytest.param(
            {
                "added_bundles": [
                    ("operator-e2e", "0.0.101"),
                    ("operator-clone-e2e", "0.0.101"),
                ],
            },
            False,
            "The PR affects more than one bundle: [('operator-clone-e2e', '0.0.101'), ('operator-e2e', '0.0.101')]",
            id="Multiple bundles",
        ),
        pytest.param(
            {
                "added_catalog_operators": [
                    ("v4.15", "operator-1"),
                    ("v4.15", "operator-2"),
                ],
            },
            True,
            None,
            id="Multiple catalog operators",
        ),
        pytest.param(
            {
                "extra_files": ["empty.txt", "operators/empty.txt"],
                "added_bundles": ["operator-e2e", "operator-clone-e2e"],
            },
            False,
            "The PR affects more than one bundle: ['operator-clone-e2e', 'operator-e2e']\n"
            "The PR affects non-operator files: ['empty.txt', 'operators/empty.txt']",
            id="Multiple issues",
        ),
        pytest.param(
            {
                "added_operators": ["operator-e2e"],
                "added_bundles": [("operator-e2e", "0.0.101")],
                "added_catalog_operators": [("v4.15", "operator-e2e")],
            },
            False,
            "The PR affects a bundle ([('operator-e2e', '0.0.101')]) and catalog ([('v4.15', 'operator-e2e')]) "
            "at the same time. Split operator and catalog changes into 2 separate pull requests.",
            id="Operator and catalog changes are mixed",
        ),
        pytest.param(
            {
                "added_bundles": [("operator-e2e", "0.0.101")],
                "deleted_bundles": [("operator-e2e", "0.0.102")],
            },
            False,
            "The PR adds and deletes bundles at the same time. This is not allowed. "
            "Please split the changes into 2 separate pull requests.",
            id="Added and deleted bundles",
        ),
        pytest.param(
            {
                "added_operators": ["operator-e2e"],
                "added_bundles": [("operator-e2e", "0.0.101")],
            },
            True,
            None,
            id="Add bundle",
        ),
        pytest.param(
            {
                "added_catalog_operators": [("v4.15", "operator-e2e")],
            },
            True,
            None,
            id="Add operator catalog",
        ),
        pytest.param(
            {
                "added_catalog_operators": [
                    ("v4.15", "operator-e2e"),
                    ("v4.15", "operator-e2e"),
                ],
                "modified_operators": ["operator-e2e", "operator-clone-e2e"],
                "modified_bundles": [],
            },
            True,
            None,
            id="Modify two operators' non-bundle files and their catalogs.",
        ),
    ],
)
def test_ParserRules_validate(
    result: Dict[str, Any], valid: bool, message: str
) -> None:
    affected_operator_collection = AffectedOperatorCollection()
    affected_bundle_collection = AffectedBundleCollection()
    affected_catalog_operator_collection = AffectedCatalogOperatorCollection()
    affected_catalog_collection = AffectedCatalogCollection()

    affected_operator_collection.added = set(result.get("added_operators", []))
    affected_operator_collection.modified = set(result.get("modified_operators", []))
    affected_operator_collection.deleted = set(result.get("deleted_operators", []))

    affected_bundle_collection.added = set(result.get("added_bundles", []))
    affected_bundle_collection.modified = set(result.get("modified_bundles", []))
    affected_bundle_collection.deleted = set(result.get("deleted_bundles", []))

    affected_catalog_operator_collection.added = set(
        result.get("added_catalog_operators", [])
    )
    affected_catalog_operator_collection.modified = set(
        result.get("modified_catalog_operators", [])
    )
    affected_catalog_operator_collection.deleted = set(
        result.get("deleted_catalog_operators", [])
    )

    affected_catalog_collection.added = set(result.get("added_catalogs", []))
    affected_catalog_collection.modified = set(result.get("modified_catalogs", []))
    affected_catalog_collection.deleted = set(result.get("deleted_catalogs", []))

    parser_results = ParserResults(
        affected_operators=affected_operator_collection,
        affected_bundles=affected_bundle_collection,
        affected_catalog_operators=affected_catalog_operator_collection,
        affected_catalogs=affected_catalog_collection,
        extra_files=result.get("extra_files", []),
    )
    validator = ParserRules(parser_results, MagicMock(), MagicMock())
    if valid:
        validator.validate()
    else:
        with pytest.raises(ValidationError) as exc:
            validator.validate()
        assert str(exc.value) == message


def test_ParserRules_validate_removal_non_fbc() -> None:
    affected_bundle_collection = AffectedBundleCollection()
    affected_operator_collection = AffectedOperatorCollection()

    head_repo = MagicMock()
    base_repo = MagicMock()

    operator_non_fbc = MagicMock()
    operator_non_fbc.config = {}
    bundle_non_fbc = MagicMock()
    bundle_non_fbc.operator = operator_non_fbc

    base_repo.operator.return_value = operator_non_fbc
    operator_non_fbc.bundle.return_value = bundle_non_fbc

    affected_operator_collection.deleted = {"operator-non-fbc"}
    affected_bundle_collection.deleted = {("operator-non-fbc", "v1.1")}

    parser_results = ParserResults(
        affected_operators=affected_operator_collection,
        affected_bundles=affected_bundle_collection,
        affected_catalog_operators=AffectedCatalogOperatorCollection(),
        affected_catalogs=AffectedCatalogCollection(),
        extra_files=set(),
    )
    validator = ParserRules(parser_results, head_repo, base_repo)
    with pytest.raises(ValidationError) as exc:
        validator.validate()
    assert str(exc.value) == (
        f"The PR deletes an existing operator: {operator_non_fbc}. This feature is only allowed for bundles with FBC enabled."
    )


def test_ParserRules_validate_removal_fbc_ok() -> None:
    affected_bundle_collection = AffectedBundleCollection()
    affected_operator_collection = AffectedOperatorCollection()

    head_repo = MagicMock()
    base_repo = MagicMock()

    operator_fbc = MagicMock()
    operator_fbc.config = {"fbc": {"enabled": True}}
    bundle_fbc = MagicMock()
    bundle_fbc.operator = operator_fbc

    base_repo.operator.return_value = operator_fbc
    operator_fbc.bundle.return_value = bundle_fbc

    affected_operator_collection.deleted = {"operator-fbc"}
    affected_bundle_collection.deleted = {("operator-fbc", "v1.1")}

    parser_results = ParserResults(
        affected_operators=affected_operator_collection,
        affected_bundles=affected_bundle_collection,
        affected_catalog_operators=AffectedCatalogOperatorCollection(),
        affected_catalogs=AffectedCatalogCollection(),
        extra_files=set(),
    )
    validator = ParserRules(parser_results, head_repo, base_repo)
    validator.validate()


@patch("yaml.safe_load_all")
@patch("builtins.open", new_callable=mock_open)
def test_ParserRules_validate_removal_fbc_fail(
    mock_open: MagicMock, mock_yaml_load: MagicMock
) -> None:
    affected_bundle_collection = AffectedBundleCollection()
    affected_operator_collection = AffectedOperatorCollection()

    head_repo = MagicMock()
    base_repo = MagicMock()

    operator_fbc = MagicMock()
    operator_fbc.config = {"fbc": {"enabled": True}}
    bundle_fbc = MagicMock()
    bundle_fbc.operator = operator_fbc
    bundle_fbc.csv = {"metadata": {"name": "foo.v1"}}

    base_repo.operator.return_value = operator_fbc
    operator_fbc.bundle.return_value = bundle_fbc

    catalog1, catalog2 = MagicMock(), MagicMock()
    head_repo.all_catalogs.return_value = [catalog1, catalog2]
    catalog1.has.return_value = False
    catalog2.has.return_value = True

    operator_catalog = MagicMock()
    catalog2.operator_catalog.return_value = MagicMock()
    bundles = [
        {
            "name": "foo.v1",
            "schema": "olm.bundle",
        },
        {
            "name": "foo.v2",
            "schema": "olm.bundle",
        },
    ]
    mock_yaml_load.return_value = iter(bundles)

    affected_operator_collection.deleted = {"operator-fbc"}
    affected_bundle_collection.deleted = {("operator-fbc", "v1.1")}

    parser_results = ParserResults(
        affected_operators=affected_operator_collection,
        affected_bundles=affected_bundle_collection,
        affected_catalog_operators=AffectedCatalogOperatorCollection(),
        affected_catalogs=AffectedCatalogCollection(),
        extra_files=set(),
    )
    validator = ParserRules(parser_results, head_repo, base_repo)
    with pytest.raises(ValidationError) as exc:
        validator.validate()
        assert (
            str(exc.value)
            == f"The PR deletes a bundle (operator-fbc/v1.1) that is in use by a catalog ({catalog2})"
        )


@pytest.mark.parametrize(
    "result, expected",
    [
        pytest.param(
            {
                "affected_bundles": ["operator-e2e/0.0.101"],
                "affected_operators": ["operator-e2e"],
                "added_or_modified_operators": ["operator-e2e"],
                "added_or_modified_bundles": ["operator-e2e/0.0.101"],
            },
            {
                "affected_bundles": ["operator-e2e/0.0.101"],
                "affected_operators": ["operator-e2e"],
                "added_or_modified_operators": ["operator-e2e"],
                "added_or_modified_bundles": ["operator-e2e/0.0.101"],
                "operator_name": "operator-e2e",
                "bundle_version": "0.0.101",
                "operator_path": "operators/operator-e2e",
                "bundle_path": "operators/operator-e2e/0.0.101",
            },
            id="Bundle is added",
        ),
        pytest.param(
            {
                "affected_bundles": [],
                "affected_operators": ["operator-e2e"],
            },
            {
                "affected_bundles": [],
                "affected_operators": ["operator-e2e"],
                "operator_name": "operator-e2e",
                "bundle_version": "",
                "operator_path": "operators/operator-e2e",
                "bundle_path": "",
            },
            id="Operator is updated",
        ),
        pytest.param(
            {
                "affected_bundles": [],
                "affected_operators": [],
            },
            {
                "affected_bundles": [],
                "affected_operators": [],
                "operator_name": "",
                "bundle_version": "",
                "operator_path": "",
                "bundle_path": "",
            },
            id="No bundle added or operator affected",
        ),
        pytest.param(
            {
                "affected_bundles": [],
                "affected_operators": [],
                "affected_catalog_operators": ["v4.16/operator-e2e"],
            },
            {
                "affected_bundles": [],
                "affected_operators": [],
                "affected_catalog_operators": ["v4.16/operator-e2e"],
                "operator_name": "operator-e2e",
                "bundle_version": "",
                "operator_path": "operators/operator-e2e",
                "bundle_path": "",
            },
            id="Catalog operator affected",
        ),
    ],
)
def test__update_result(result: dict[str, Any], expected: dict[str, Any]) -> None:
    parsed_result = ParserResults(
        MagicMock(), MagicMock(), MagicMock(), MagicMock(), set()
    )
    parsed_result.enrich_result(result)
    assert result == expected
