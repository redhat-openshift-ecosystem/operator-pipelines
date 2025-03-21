"""Check permissions for a pull request and request a review if needed"""

import argparse
import json
import logging
import os
import urllib
from typing import Any

from github import (
    Auth,
    Github,
    UnknownObjectException,
    GithubException,
)
from operatorcert import pyxis
from operatorcert.github import add_labels_to_pull_request, parse_github_issue_url
from operatorcert.logger import setup_logger
from operatorcert.operator_repo import Operator
from operatorcert.operator_repo import Repo as OperatorRepo
from operatorcert.utils import run_command

LOGGER = logging.getLogger("operator-cert")


class NoPermissionError(Exception):
    """Exception raised when user does not have permissions to submit a PR"""


class MaintainersReviewNeeded(Exception):
    """Exception raised when maintainer review is needed"""


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        argparse.ArgumentParser: Argument parser
    """
    parser = argparse.ArgumentParser(description="Review a user permissions for PR.")
    parser.add_argument(
        "--repo-base-path",
        default=".",
        help="Path to the base git repository",
    )
    parser.add_argument(
        "--repo-head-path",
        default=".",
        help="Path to the head git repository",
    )
    parser.add_argument(
        "--changes-file",
        help="A file with changes between the base and head repositories",
    )
    parser.add_argument(
        "--pyxis-url",
        default="https://pyxis.engineering.redhat.com",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument("--pull-request-url", help="URL to the pull request")
    parser.add_argument("--pr-owner", help="Owner of the pull request")
    parser.add_argument(
        "--output-file", help="Path to a json file where results will be stored"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


class OperatorReview:
    """
    A class represents a pull request review and permissions check
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        operator: Operator,
        pr_owner: str,
        base_repo: OperatorRepo,
        head_repo: OperatorRepo,
        pull_request_url: str,
        pyxis_url: str,
    ) -> None:
        self.operator = operator
        self.pr_owner = pr_owner
        self.base_repo = base_repo
        self.head_repo = head_repo
        self.pull_request_url = pull_request_url
        self.pyxis_url = pyxis_url

    @property
    def base_repo_config(self) -> dict[str, Any]:
        """
        A dictionary with the base repository configuration

        Returns:
            dict: A dictionary with the base repository configuration
        """
        return self.base_repo.config or {}

    @property
    def head_repo_operator_config(self) -> dict[str, Any]:
        """
        A dictionary with the head repository operator configuration

        Returns:
            dict: A dictionary with the head repository operator configuration
        """
        return self.operator.config or {}

    @property
    def base_repo_operator_config(self) -> dict[str, Any]:
        """
        A dictionary with the base repository operator configuration

        Returns:
            dict[str, Any]: A dictionary with the base repository operator
            configuration
        """
        if not self.base_repo.has(self.operator.operator_name):
            return {}  # pragma: no cover
        base_repo_operator = self.base_repo.operator(self.operator.operator_name)
        return base_repo_operator.config or {}

    def is_partner(self) -> bool:
        """
        Check if the operator is a partner operator based on the
        certification project id

        Returns:
            bool: A boolean value indicating if the operator is a partner operator
        """
        return bool(self.cert_project_id)

    @property
    def cert_project_id(self) -> str:
        """
        A certification project id from the operator config file

        Returns:
            str: A certification project id
        """
        return self.head_repo_operator_config.get("cert_project_id") or ""

    @property
    def reviewers(self) -> list[str]:
        """
        Operator reviewers from the operator config file

        Returns:
            list[str]: A list of github users who are reviewers for the
            operator in lowercase format
        """
        reviewers = self.base_repo_operator_config.get("reviewers") or []

        # Github supports case-insensitive usernames - convert all usernames to lowercase
        # to avoid issues with case sensitivity
        return [user.lower() for user in reviewers]

    @property
    def maintainers(self) -> list[str]:
        """
        Repository maintainers from the root config file

        Returns:
            list[str]: A list of github users who are maintainers for the repo
        """
        return self.base_repo_config.get("maintainers") or []

    @property
    def github_repo_org(self) -> str:
        """
        A github repository organization parsed from the pull request url

        Returns:
            str: Github organization
        """
        return urllib.parse.urlparse(self.pull_request_url).path.split("/")[1]

    @property
    def github_repo_name(self) -> str:
        """
        The name of the github repo the pull request belongs to

        Returns:
            str: the github repo name in the form "organization_name/repo_name"
        """
        return "/".join(
            urllib.parse.urlparse(self.pull_request_url).path.split("/")[1:3]
        )

    @property
    def pr_labels(self) -> set[str]:
        """
        The set of labels applied to the pull request

        Returns:
            set[str]: the labels applied to the pull request
        """
        github_auth = Auth.Token(os.environ.get("GITHUB_TOKEN") or "")
        github = Github(auth=github_auth)
        pr_no = int(urllib.parse.urlparse(self.pull_request_url).path.split("/")[-1])
        return {
            x.name
            for x in github.get_repo(self.github_repo_name).get_pull(pr_no).get_labels()
        }

    def check_permissions(self) -> bool:
        """
        Check if the pull request owner has permissions to submit a PR for the operator

        Returns:
            bool: A boolean value indicating if the user has permissions to submit a PR
        """
        LOGGER.info("Checking permissions for operator %s", self.operator.operator_name)
        if self.is_org_member():
            # Members of the organization have permissions to submit a PR
            return True
        if self.is_partner():
            return self.check_permission_for_partner()
        if self.check_permission_for_community():
            return True
        # Enable PR approval on forked repository
        # and approves rh-operator-bundle-bot PRs
        return self.pr_owner_can_write()

    def is_org_member(self) -> bool:
        """
        Check if the pull request owner is a member of the organization

        Returns:
            bool: A boolean value indicating if the user is a member of the organization
        """
        LOGGER.info(
            "Checking if the pull request owner is a member of the organization"
        )
        github_auth = Auth.Token(os.environ.get("GITHUB_TOKEN") or "")
        github = Github(auth=github_auth)
        try:
            members = github.get_organization(self.github_repo_org).get_members()
        except UnknownObjectException:
            LOGGER.info("Organization %s does not exist", self.github_repo_org)
            return False

        for member in members:
            if self.pr_owner in member.login:
                LOGGER.info(
                    "Pull request owner '%s' is a member of the organization '%s'",
                    self.pr_owner,
                    self.github_repo_org,
                )
                return True
        LOGGER.info(
            "Pull request owner '%s' is not a member of the organization '%s'",
            self.pr_owner,
            self.github_repo_org,
        )
        return False

    def pr_owner_can_write(self) -> bool:
        """
        Check if the pull request owner has write permissions for the repository

        Returns:
            bool: A boolean value indicating if the user
                  has write permissions for the repository
        """
        LOGGER.info(
            "Checking if the pull request owner has write permissions for the repository"
        )
        github_auth = Auth.Token(os.environ.get("GITHUB_TOKEN") or "")
        github = Github(auth=github_auth)
        repo = github.get_repo(self.github_repo_name)
        try:
            permission = repo.get_collaborator_permission(self.pr_owner)
        except GithubException:
            LOGGER.info(
                "Cannot get permissions for the pull request owner '%s'", self.pr_owner
            )
            return False
        if permission in ["admin", "write"]:
            LOGGER.info(
                "Pull request owner '%s' has write permissions for the repository",
                self.pr_owner,
            )
            return True
        return False

    def check_permission_for_partner(self) -> bool:
        """
        Check if the pull request owner has permissions to submit a PR for the for
        partner operator.
        A user has permissions to submit a PR if the user is listed in the certification
        project in Pyxis.

        Raises:
            NoPermissionError: An exception raised when user does not have permissions
            to submit a PR

        Returns:
            bool: A boolean value indicating if the user has permissions to submit a PR
        """
        project = pyxis.get_project(self.pyxis_url, self.cert_project_id)
        if not project:
            raise NoPermissionError(
                f"Project {self.cert_project_id} does not exist and pipeline can't "
                "verify permissions."
            )
        container = project.get("container") or {}
        usernames = container.get("github_usernames") or []
        if self.pr_owner not in usernames:
            raise NoPermissionError(
                f"User {self.pr_owner} does not have permissions to submit a PR for "
                f"project {self.cert_project_id}. Users with permissions: {usernames}. "
                f"Add {self.pr_owner} to the list of operator owners in Red Hat Connect."
            )
        LOGGER.info(
            "Pull request owner %s can submit PR for operator %s",
            self.pr_owner,
            self.operator.operator_name,
        )
        return True

    def check_permission_for_community(self) -> bool:
        """
        Check if the pull request owner has permissions to submit a PR for the
        operator in community repository.

        The function checks a local reviewers from the operator config file and fallback
        to global repo config.

        Raises:
            MaintainersReviewNeeded: An exception raised when maintainer review is needed

        Returns:
            bool: A boolean value indicating if the user has permissions to submit a PR
        """
        if not self.reviewers:
            # If there are no reviewers in the operator config file or operator is new,
            # we need to request a review from maintainers
            raise MaintainersReviewNeeded(
                f"{self.operator} does not have any reviewers in the base repository "
                "or is brand new."
            )

        if self.pr_owner.lower() in self.reviewers:
            LOGGER.info(
                "Pull request owner %s can submit PR for operator %s",
                self.pr_owner,
                self.operator.operator_name,
            )
            return True

        LOGGER.info("Checking if the pull request is approved by a reviewer")
        if "approved" in self.pr_labels:
            LOGGER.info("Pull request is approved by a reviewer")
            return True

        LOGGER.info(
            "Pull request owner %s is not in the list of reviewers %s",
            self.pr_owner,
            self.reviewers,
        )
        self.request_review_from_owners()
        return False

    def request_review_from_maintainers(self) -> None:
        """
        Request review from the operator maintainers by adding a comment to the PR.
        """
        LOGGER.info(
            "Requesting a review from maintainers for the pull request: %s",
            self.pull_request_url,
        )
        maintainers_with_at = ", ".join(map(lambda x: f"@{x}", self.maintainers))
        comment_text = (
            "This PR requires a review from repository maintainers.\n"
            f"{maintainers_with_at}: please review the PR and approve it with an "
            "`approved` label if the pipeline is still running or merge the PR "
            "directly after review if the pipeline already passed successfully."
        )
        run_command(
            ["gh", "pr", "comment", self.pull_request_url, "--body", comment_text]
        )

    def request_review_from_owners(self) -> None:
        """
        Request review from the operator owners by adding a comment to the PR.
        """
        reviewers_with_at = ", ".join(map(lambda x: f"@{x}", self.reviewers))
        comment_text = (
            "The author of the PR is not listed as one of the reviewers in ci.yaml.\n"
            f"{reviewers_with_at}: please review the PR and approve it with an "
            "`/approve` comment.\n\n"
            "Consider adding the author of the PR to the list of reviewers in "
            "the ci.yaml file if you want automated merge without explicit "
            "approval."
        )

        run_command(
            ["gh", "pr", "comment", self.pull_request_url, "--body", comment_text]
        )


def extract_operators_from_catalog(
    head_repo: OperatorRepo, catalog_operators: list[str]
) -> set[Operator]:
    """
    Map the affected catalog operators to the actual operators

    Args:
        head_repo (OperatorRepo): A head git repository
        catalog_operators (list[str]): List of affected catalog operators

    Returns:
        set[Operator]: A set of operators
    """
    operators = set()
    for catalog_operator in catalog_operators:
        catalog, operator_name = catalog_operator.split("/")
        # We need to get the operator from the catalog to get the actual operator
        operator = head_repo.catalog(catalog).operator_catalog(operator_name).operator
        operators.add(operator)
    return operators


def check_permissions(
    base_repo: OperatorRepo,
    head_repo: OperatorRepo,
    args: Any,
) -> bool:
    """
    Check permission for the pull request owner and request a review if
    needed or fail if the user does not have permissions

    Args:
        base_repo (OperatorRepo): A base git repository
        head_repo (OperatorRepo): A head git repository
        args (Any): CLI arguments

    Returns:
        bool: A boolean value indicating if the user has permissions to submit a PR
    """
    LOGGER.info("Checking permissions for the pull request owner: %s", args.pr_owner)

    with open(args.changes_file, "r", encoding="utf8") as f:
        changes = json.load(f)

    # Get added and modified operators from head repo
    added_or_updated_operators = changes.get("added_operators", [])
    added_or_updated_operators.extend(changes.get("modified_operators", []))
    operators = {
        head_repo.operator(operator) for operator in added_or_updated_operators
    }

    # Get deleted operators from base repo
    operators = operators.union(
        {
            base_repo.operator(operator)
            for operator in changes.get("deleted_operators", [])
        }
    )

    # In this step we need to map the affected catalog operators to the actual
    # operators. This needs to be done because the permission and reviewers
    # are stored in the operator config file
    affected_catalog_operators = changes.get("added_catalog_operators", [])
    affected_catalog_operators.extend(changes.get("modified_catalog_operators", []))
    operators = operators.union(
        extract_operators_from_catalog(head_repo, affected_catalog_operators)
    )
    removed_catalog_operators = changes.get("removed_catalog_operators", [])
    operators = operators.union(
        extract_operators_from_catalog(base_repo, removed_catalog_operators)
    )

    is_approved = []
    for operator in operators:
        operator_review = OperatorReview(
            operator,
            args.pr_owner,
            base_repo,
            head_repo,
            args.pull_request_url,
            args.pyxis_url,
        )
        try:
            result = operator_review.check_permissions()
            is_approved.append(result)
        except MaintainersReviewNeeded as exc:
            LOGGER.info(
                f"Operator %s requires a review from maintainers. {exc}",
                operator.operator_name,
            )
            operator_review.request_review_from_maintainers()
            is_approved.append(False)

    return all(is_approved)


def add_label_approved(pull_request_url: str) -> None:
    """
    Add 'approved' label to the pull request

    Args:
        pull_request_url (str): URL to the pull request
    """
    repository_name, pr_id = parse_github_issue_url(pull_request_url)
    github_auth = Auth.Token(os.environ.get("GITHUB_TOKEN") or "")
    github = Github(auth=github_auth)
    repository = github.get_repo(repository_name)
    pull_request = repository.get_pull(pr_id)
    add_labels_to_pull_request(pull_request, ["approved"])


def main() -> None:
    """
    Main function of the script
    """
    # Args
    parser = setup_argparser()
    args = parser.parse_args()

    # Logging
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    base_repo = OperatorRepo(args.repo_base_path)
    head_repo = OperatorRepo(args.repo_head_path)

    is_approved = check_permissions(base_repo, head_repo, args)

    if is_approved:
        add_label_approved(args.pull_request_url)

    # Save the results to a file
    output = {
        "approved": is_approved,
    }
    if args.output_file:
        with open(args.output_file, "w", encoding="utf8") as f:
            json.dump(output, f)


if __name__ == "__main__":  # pragma: no cover
    main()
