from pathlib import Path
from typing import Any
from unittest import mock
from unittest.mock import MagicMock, call, patch

import operatorcert.entrypoints.check_permissions as check_permissions
import pytest
from github import GithubException, UnknownObjectException
from operatorcert.operator_repo import Repo as OperatorRepo
from tests.operator_repo import bundle_files, create_files


@pytest.fixture
def review_partner(tmp_path: Path) -> check_permissions.OperatorReview:
    create_files(
        tmp_path,
        bundle_files(
            "test-operator",
            "0.0.1",
            other_files={
                "operators/test-operator/ci.yaml": {
                    "cert_project_id": "cert_project_id"
                }
            },
        ),
    )
    base_repo = OperatorRepo(tmp_path)
    head_repo = OperatorRepo(tmp_path)
    operator = head_repo.operator("test-operator")
    return check_permissions.OperatorReview(
        operator,
        "owner",
        base_repo,
        head_repo,
        "https://github.com/my-org/repo-123/pulls/1",
        "pyxis_url",
    )


@pytest.fixture
def review_community(tmp_path: Path) -> check_permissions.OperatorReview:
    create_files(
        tmp_path,
        bundle_files(
            "test-operator",
            "0.0.1",
            other_files={
                "operators/test-operator/ci.yaml": {
                    "reviewers": ["User1", "user2"],
                },
                "config.yaml": {"maintainers": ["maintainer1", "maintainer2"]},
            },
        ),
    )

    base_repo = OperatorRepo(tmp_path)
    head_repo = OperatorRepo(tmp_path)
    operator = head_repo.operator("test-operator")
    return check_permissions.OperatorReview(
        operator,
        "owner",
        base_repo,
        head_repo,
        "https://github.com/my-org/repo-123/pulls/1",
        "pyxis_url",
    )


def test_OperatorReview(review_partner: check_permissions.OperatorReview) -> None:
    assert review_partner.base_repo_config == review_partner.base_repo.config
    assert review_partner.head_repo_operator_config == review_partner.operator.config


@patch("operatorcert.entrypoints.check_permissions.Github")
@patch("operatorcert.entrypoints.check_permissions.Auth.Token")
def test_OperatorReview_github_client(
    mock_token: MagicMock,
    mock_github: MagicMock,
    review_partner: check_permissions.OperatorReview,
) -> None:
    assert review_partner.github_client == mock_github.return_value


def test_OperatorReview_base_repo_operator_config(
    review_partner: check_permissions.OperatorReview,
) -> None:
    assert review_partner.base_repo_operator_config == {
        "cert_project_id": "cert_project_id"
    }


def test_OperatorReview_cert_project_id(
    review_partner: check_permissions.OperatorReview,
) -> None:
    assert review_partner.cert_project_id == "cert_project_id"

    assert review_partner.is_partner() == True


def test_OperatorReview_reviewers(
    review_community: check_permissions.OperatorReview,
) -> None:
    assert review_community.reviewers == ["user1", "user2"]


def test_OperatorReview_maintainers(
    review_community: check_permissions.OperatorReview,
) -> None:
    assert review_community.maintainers == ["maintainer1", "maintainer2"]


def test_OperatorReview_github_repo_org(
    review_community: check_permissions.OperatorReview,
) -> None:
    assert review_community.github_repo_org == "my-org"


def test_OperatorReview_github_repo_name(
    review_community: check_permissions.OperatorReview,
) -> None:
    assert review_community.github_repo_name == "my-org/repo-123"


@patch("operatorcert.entrypoints.check_permissions.OperatorReview.github_client")
def test_OperatorReview_pr_labels(
    mock_github: MagicMock,
    review_community: check_permissions.OperatorReview,
) -> None:
    repo = MagicMock()
    pull = MagicMock()

    def _mock_label(name: str) -> MagicMock:
        m = MagicMock()
        m.name = name
        return m

    pull.get_labels.return_value = [_mock_label("foo"), _mock_label("bar")]
    repo.get_pull.return_value = pull
    mock_github.get_repo.return_value = repo
    assert review_community.pr_labels == {"foo", "bar"}


@pytest.mark.parametrize(
    "is_org_member, is_partner, owner_can_write, permission_partner, permission_community, is_catalog_promotion_pr, permission_partner_called, permission_community_called, expected_result",
    [
        pytest.param(
            True, False, False, False, False, False, False, False, True, id="org member"
        ),
        pytest.param(
            False,
            True,
            False,
            True,
            False,
            False,
            True,
            False,
            True,
            id="partner - approved",
        ),
        pytest.param(
            False,
            True,
            False,
            False,
            False,
            False,
            True,
            False,
            False,
            id="partner - denied",
        ),
        pytest.param(
            False,
            False,
            True,
            False,
            False,
            False,
            False,
            True,
            True,
            id="owner - approved",
        ),
        pytest.param(
            False,
            False,
            False,
            False,
            True,
            False,
            False,
            True,
            True,
            id="community - approved",
        ),
        pytest.param(
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            True,
            False,
            id="community - denied",
        ),
        pytest.param(
            True,
            False,
            False,
            False,
            False,
            True,
            False,
            True,
            False,
            id="owner, but PR with catalog promotion - denied",
        ),
    ],
)
@patch(
    "operatorcert.entrypoints.check_permissions.OperatorReview.check_permission_for_community"
)
@patch(
    "operatorcert.entrypoints.check_permissions.OperatorReview.check_permission_for_partner"
)
@patch("operatorcert.entrypoints.check_permissions.OperatorReview.is_partner")
@patch("operatorcert.entrypoints.check_permissions.OperatorReview.is_org_member")
@patch("operatorcert.entrypoints.check_permissions.OperatorReview.pr_owner_can_write")
@patch(
    "operatorcert.entrypoints.check_permissions.OperatorReview.is_catalog_promotion_pr"
)
def test_OperatorReview_check_permissions(
    mock_is_catalog_promotion_pr: MagicMock,
    mock_pr_owner_can_write: MagicMock,
    mock_is_org_member: MagicMock,
    mock_is_partner: MagicMock,
    mock_check_permission_for_partner: MagicMock,
    mock_check_permission_for_community: MagicMock,
    review_community: check_permissions.OperatorReview,
    is_org_member: bool,
    is_partner: bool,
    owner_can_write: bool,
    permission_partner: bool,
    permission_community: bool,
    is_catalog_promotion_pr: bool,
    permission_partner_called: bool,
    permission_community_called: bool,
    expected_result: bool,
) -> None:
    mock_is_catalog_promotion_pr.return_value = is_catalog_promotion_pr
    mock_is_org_member.return_value = is_org_member
    mock_is_partner.return_value = is_partner
    mock_pr_owner_can_write.return_value = owner_can_write
    mock_check_permission_for_partner.return_value = permission_partner
    mock_check_permission_for_community.return_value = permission_community
    assert review_community.check_permissions() == expected_result

    if permission_partner_called:
        mock_check_permission_for_partner.assert_called_once()
    else:
        mock_check_permission_for_partner.assert_not_called()

    if permission_community_called:
        mock_check_permission_for_community.assert_called_once()
    else:
        mock_check_permission_for_community.assert_not_called()


@patch("operatorcert.entrypoints.check_permissions.OperatorReview.github_client")
def test_OperatorReview_is_catalog_promotion_pr(
    mock_github_client: MagicMock, review_community: check_permissions.OperatorReview
) -> None:
    # Test with a PR URL that contains "catalog-promotion"
    class Label:
        def __init__(self, name: str) -> None:
            self.name = name

    mock_github_client.get_repo.return_value.get_pull.return_value.get_labels.return_value = [
        Label("catalog-promotion/review-needed"),
        Label("other-label"),
    ]
    assert review_community.is_catalog_promotion_pr() == True

    mock_github_client.get_repo.return_value.get_pull.return_value.get_labels.return_value = [
        Label("other-label"),
    ]
    assert review_community.is_catalog_promotion_pr() == False

    mock_github_client.get_repo.return_value.get_pull.return_value.get_labels.side_effect = UnknownObjectException(
        404, "", {}
    )
    assert review_community.is_catalog_promotion_pr() == False


@patch("operatorcert.entrypoints.check_permissions.OperatorReview.github_client")
def test_OperatorReview_is_org_member(
    mock_github: MagicMock,
    review_community: check_permissions.OperatorReview,
) -> None:
    # User is a member of the organization
    mock_organization = MagicMock()
    members = [MagicMock(login="user123"), MagicMock(login="owner")]
    mock_organization.get_members.return_value = members
    mock_github.get_organization.return_value = mock_organization
    assert review_community.is_org_member() == True

    # User is not a member of the organization
    members = [MagicMock(login="user123")]
    mock_organization.get_members.return_value = members
    assert review_community.is_org_member() == False

    # Organization does not exist
    members = [MagicMock(login="user123")]
    mock_github.get_organization.side_effect = UnknownObjectException(404, "", {})
    assert review_community.is_org_member() == False


@patch("operatorcert.entrypoints.check_permissions.OperatorReview.github_client")
def test_OperatorReview_pr_owner_can_write(
    mock_github: MagicMock,
    review_community: check_permissions.OperatorReview,
) -> None:
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    # User can write to the repository
    mock_repo.get_collaborator_permission.return_value = "write"
    assert review_community.pr_owner_can_write() == True

    # User cannot write to the repository
    mock_repo.get_collaborator_permission.return_value = "read"
    assert review_community.pr_owner_can_write() == False

    # Cannot get collaborator permission
    mock_repo.get_collaborator_permission.side_effect = GithubException(404, "", {})
    assert review_community.pr_owner_can_write() == False


@pytest.mark.parametrize(
    ["project", "valid"],
    [
        pytest.param(None, False, id="no project"),
        pytest.param({}, False, id="no container"),
        pytest.param({"container": {}}, False, id="no github_usernames"),
        pytest.param(
            {"container": {"github_usernames": None}}, False, id="no github_usernames"
        ),
        pytest.param(
            {"container": {"github_usernames": ["user123"]}},
            False,
            id="user not in github_usernames",
        ),
        pytest.param(
            {"container": {"github_usernames": ["owner"]}},
            True,
            id="user in github_usernames",
        ),
    ],
)
@patch("operatorcert.entrypoints.check_permissions.pyxis.get_project")
def test_OperatorReview_check_permission_for_partner(
    mock_pyxis_project: MagicMock,
    review_partner: check_permissions.OperatorReview,
    project: dict[str, Any],
    valid: bool,
) -> None:
    mock_pyxis_project.return_value = project
    if valid:
        assert review_partner.check_permission_for_partner() == True
    else:
        with pytest.raises(check_permissions.NoPermissionError):
            review_partner.check_permission_for_partner()


@pytest.mark.parametrize(
    ["reviewers", "labels", "owners_review", "result"],
    [
        pytest.param(
            [],
            set(),
            False,
            check_permissions.MaintainersReviewNeeded,
            id="No reviewers",
        ),
        pytest.param(
            ["owner", "foo"],
            set(),
            False,
            True,
            id="author is reviewer",
        ),
        pytest.param(
            ["foo", "bar"],
            set(),
            True,
            False,
            id="author is not reviewer",
        ),
        pytest.param(
            ["bar", "baz"],
            {"approved"},
            False,
            True,
            id="author is not reviewer, PR approved",
        ),
    ],
)
@patch(
    "operatorcert.entrypoints.check_permissions.OperatorReview.request_review_from_owners"
)
@patch(
    "operatorcert.entrypoints.check_permissions.OperatorReview.reviewers",
    new_callable=mock.PropertyMock,
)
@patch(
    "operatorcert.entrypoints.check_permissions.OperatorReview.pr_labels",
    new_callable=mock.PropertyMock,
)
def test_OperatorReview_check_permission_for_community(
    mock_labels: MagicMock,
    mock_reviewers: MagicMock,
    mock_review_from_owners: MagicMock,
    review_community: check_permissions.OperatorReview,
    reviewers: list[str],
    labels: set[str],
    owners_review: bool,
    result: bool | type,
) -> None:
    mock_reviewers.return_value = reviewers
    mock_labels.return_value = labels

    if isinstance(result, bool):
        assert review_community.check_permission_for_community() == result
    else:
        with pytest.raises(result):
            review_community.check_permission_for_community()

    if owners_review:
        mock_review_from_owners.assert_called_once()
    else:
        mock_review_from_owners.assert_not_called()


@patch("operatorcert.entrypoints.check_permissions.run_command")
def test_OperatorReview_request_review_from_maintainers(
    mock_command: MagicMock,
    review_community: check_permissions.OperatorReview,
) -> None:
    review_community.request_review_from_maintainers()
    mock_command.assert_called_once_with(
        [
            "gh",
            "pr",
            "comment",
            review_community.pull_request_url,
            "--body",
            "This PR requires a review from repository maintainers.\n"
            f"@maintainer1, @maintainer2: please review the PR and approve it with an "
            "`approved` label if the pipeline is still running or merge the PR "
            "directly after review if the pipeline already passed successfully.",
        ]
    )


@patch("operatorcert.entrypoints.check_permissions.run_command")
def test_OperatorReview_request_review_from_owners(
    mock_command: MagicMock,
    review_community: check_permissions.OperatorReview,
) -> None:
    review_community.request_review_from_owners()
    mock_command.assert_called_once_with(
        [
            "gh",
            "pr",
            "comment",
            review_community.pull_request_url,
            "--body",
            "The author of the PR is not listed as one of the reviewers in ci.yaml.\n"
            "@user1, @user2: please review the PR and approve it with an `/approve` comment.\n\n"
            "Consider adding the author of the PR to the list of reviewers in "
            "the ci.yaml file if you want automated merge without explicit "
            "approval.",
        ]
    )


def test_extract_operators_from_catalog() -> None:
    catalog_operators = [
        "catalog1/operator1",
        "catalog1/operator2",
        "catalog2/operator3",
    ]
    head_repo = MagicMock()
    result = check_permissions.extract_operators_from_catalog(
        head_repo, catalog_operators
    )
    assert result == set(
        [
            head_repo.catalog("catalog1").operator_catalog("operator1").operator,
            head_repo.catalog("catalog1").operator_catalog("operator2").operator,
            head_repo.catalog("catalog2").operator_catalog("operator3").operator,
        ]
    )


@patch("operatorcert.entrypoints.check_permissions.OperatorReview")
@patch("operatorcert.entrypoints.check_permissions.extract_operators_from_catalog")
@patch("operatorcert.entrypoints.check_permissions.json.load")
@patch("builtins.open")
def test_check_permissions(
    mock_open: MagicMock,
    mock_json_load: MagicMock,
    mock_catalog_operators: MagicMock,
    mock_review: MagicMock,
) -> None:
    pass

    base_repo = MagicMock()
    head_repo = MagicMock()

    mock_json_load.return_value = {
        "added_operators": ["operator1"],
        "modified_operators": ["operator2"],
        "deleted_operators": ["operator3"],
        "added_catalog_operators": ["c1/operator4"],
        "modified_catalog_operators": ["c2/operator5"],
        "removed_catalog_operators": ["c3/operator6"],
    }
    head_repo.operator.side_effect = [
        MagicMock(name="operator1"),
        MagicMock(name="operator2"),
    ]
    base_repo.operator.side_effect = [
        MagicMock(name="operator3"),
        MagicMock(name="operator6"),
    ]
    mock_review.return_value.check_permissions.side_effect = [
        False,
        check_permissions.MaintainersReviewNeeded("error"),
        True,
        True,
        True,
        True,
    ]
    mock_catalog_operators.side_effect = [
        set(
            [
                MagicMock(name="operator4"),
                MagicMock(name="operator5"),
            ]
        ),
        set(
            [
                MagicMock(name="operator6"),
            ]
        ),
    ]

    result = check_permissions.check_permissions(base_repo, head_repo, MagicMock())
    assert not result

    head_repo.operator.assert_has_calls([call("operator1"), call("operator2")])
    base_repo.operator.assert_has_calls([call("operator3")])
    mock_catalog_operators.assert_has_calls(
        [
            call(head_repo, ["c1/operator4", "c2/operator5"]),
            call(base_repo, ["c3/operator6"]),
        ]
    )


@patch("operatorcert.entrypoints.check_permissions.Github")
@patch("operatorcert.entrypoints.check_permissions.Auth.Token")
@patch("operatorcert.entrypoints.check_permissions.add_labels_to_pull_request")
def test_add_label_approved(
    mock_add_labels: MagicMock,
    mock_token: MagicMock,
    mock_github: MagicMock,
) -> None:
    mock_repo = MagicMock()
    mock_github.return_value.get_repo.return_value = mock_repo
    mock_pull = MagicMock()
    mock_repo.get_pull.return_value = mock_pull

    check_permissions.add_label_approved("https://github.com/my-org/repo-123/pulls/1")
    mock_github.return_value.get_repo.assert_has_calls([call("my-org/repo-123")])
    mock_repo.get_pull.assert_called_once_with(1)
    mock_add_labels.assert_called_once_with(mock_pull, ["approved"])


@patch("operatorcert.entrypoints.check_permissions.json.dump")
@patch("operatorcert.entrypoints.check_permissions.add_label_approved")
@patch("operatorcert.entrypoints.check_permissions.check_permissions")
@patch("operatorcert.entrypoints.check_permissions.OperatorRepo")
@patch("operatorcert.entrypoints.check_permissions.setup_logger")
@patch("operatorcert.entrypoints.check_permissions.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_operator_repo: MagicMock,
    mock_check_permissions: MagicMock,
    mock_add_label_approved: MagicMock,
    mock_json_dump: MagicMock,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    create_files(tmp_path, {"some_file": "foo"})
    args = MagicMock()
    args.catalog_names = ["catalog1", "catalog2"]
    args.repo_base_path = str(tmp_path / "repo-base")
    args.repo_head_path = str(tmp_path / "repo-head")
    args.output_file = tmp_path / "output.json"

    base_repo = MagicMock()
    head_repo = MagicMock()

    mock_operator_repo.side_effect = [base_repo, head_repo]

    mock_setup_argparser.return_value.parse_args.return_value = args
    mock_check_permissions.return_value = True

    check_permissions.main()

    mock_check_permissions.assert_called_once_with(base_repo, head_repo, args)
    mock_add_label_approved.assert_called_once_with(args.pull_request_url)

    expected_output = {
        "approved": mock_check_permissions.return_value,
    }
    mock_json_dump.assert_called_once_with(expected_output, mock.ANY)


def test_setup_argparser() -> None:
    assert check_permissions.setup_argparser() is not None
