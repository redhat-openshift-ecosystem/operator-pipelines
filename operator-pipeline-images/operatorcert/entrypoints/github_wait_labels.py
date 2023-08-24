"""
CLI utility to wait on pull request labels conditionally.
"""
import argparse as ap
import re
import os
from enum import Enum
import time
import logging

from github import Auth, Github

from github.PullRequest import PullRequest
from github.Repository import Repository
from github.GithubException import GithubException

from operatorcert.entrypoints.github_labels import parse_github_issue_url
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


class WaitType(Enum):
    """
    Enum representing the possible label wait conditions

    WaitAny -> Wait until at least one label matches at least one regular expression
    WaitNone -> Wait until no label matches any regular expression
    """

    WaitAny = 0
    WaitNone = 1


class WaitCondition:
    """
    Class representing a condition that must hold for labels on a PR
    """

    def __init__(self, wait_type: WaitType, regexp: str) -> None:
        self.wait_type = wait_type
        self.regexp = regexp
        self.pattern = re.compile(regexp)

    def holds(self, labels: list[str]) -> bool:
        if self.wait_type == WaitType.WaitAny:
            return any(self.pattern.fullmatch(label) for label in labels)

        if self.wait_type == WaitType.WaitNone:
            return not any(self.pattern.fullmatch(label) for label in labels)

    @staticmethod
    def get_wait_conditions(args: ap.Namespace) -> list["WaitCondition"]:
        """
        Parse all required wait conditions from program args
        """
        conditions = []

        for regexp in args.any:
            conditions.append(WaitCondition(WaitType.WaitAny, regexp))

        for regexp in args.none:
            conditions.append(WaitCondition(WaitType.WaitNone, regexp))

        return conditions

    def __eq__(self, __value: object) -> bool:  # pragma: nocover
        if not isinstance(__value, WaitCondition):
            return False

        return self.wait_type == __value.wait_type and self.regexp == __value.regexp


def setup_argparser() -> ap.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = ap.ArgumentParser(description="GitHub cli tool to wait on labels to PR.")

    parser.add_argument(
        "--any",
        action="append",
        default=[],
        help="Wait until at least one label matches the regular expression.",
    )

    parser.add_argument(
        "--none",
        action="append",
        default=[],
        help="Wait until no labels match the regular expression.",
    )

    parser.add_argument(
        "--github-host-url",
        default="https://api.github.com",
        help="The GitHub host, default: https://api.github.com",
    )

    parser.add_argument(
        "--pull-request-url",
        required=True,
        help="The GitHub pull request URL where we want to wait for labels.",
    )

    parser.add_argument("--timeout", default=60, help="Timeout for waiting in seconds.")

    parser.add_argument(
        "--poll-interval", default=1, help="Interval between requests in seconds"
    )

    return parser


def get_pr_labels(
    repository: Repository,
    pull_request_id: int,
) -> list[str]:
    """
    Get labels on a PR in a repository by PR id
    """
    try:
        pull_request: PullRequest = repository.get_pull(pull_request_id)
    except GithubException as exc:
        LOGGER.error("Unable to get pull request: %s", str(exc))
        exit(1)

    label_names = [label.name for label in pull_request.labels]

    return label_names


def wait_on_pr_labels(
    repository: Repository,
    pull_request_id: int,
    wait_conditions: list[WaitCondition],
    timeout_s: int,
    poll_interval_s: int,
) -> bool:
    """
    Wait until ALL wait conditions on PR labels hold

    Args:
        repository: PyGithub repository object
        pull_request_id: Github pull request id
        timeout_s: Timeout for waiting on label changes in seconds
        wait_conditions: List of conditions that must hold for a wait to end
        poll_interval_s: Interval between finished requests to GitHub API
    """
    assert poll_interval_s < timeout_s

    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout_s:
        pr_labels = get_pr_labels(repository, pull_request_id)

        if all(condition.holds(pr_labels) for condition in wait_conditions):
            for label in pr_labels:
                print(label)

            return True

        time.sleep(poll_interval_s)

    return False


def main():
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    setup_logger(level=log_level)

    github_auth = Auth.Token(os.environ["GITHUB_TOKEN"])
    github = Github(auth=github_auth)

    repo_url, pull_request_id = parse_github_issue_url(args.pull_request_url)

    try:
        repository = github.get_repo(repo_url)
    except GithubException as exc:
        LOGGER.error("Unable to get repository from GitHub: %s", str(exc))
        exit(2)

    conditions = WaitCondition.get_wait_conditions(args)
    if not wait_on_pr_labels(
        repository,
        pull_request_id,
        conditions,
        args.timeout,
        args.poll_interval,
    ):
        exit(1)

    exit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
