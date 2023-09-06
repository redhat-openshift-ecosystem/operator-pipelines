"""
CLI utility to wait on pull request labels conditionally.
"""
import argparse as ap
import logging
import os
import re
import sys
import time
from enum import Enum

from github import Auth, Github
from github.GithubException import GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository
from operatorcert.entrypoints.github_labels import parse_github_issue_url
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


class WaitType(Enum):
    """
    Enum representing the possible label wait conditions

    WAIT_ANY -> Wait until at least one label matches the regular expression
    WAIT_NONE -> Wait until no label matches the regular expression
    """

    WAIT_ANY = 0
    WAIT_NONE = 1


class WaitCondition:
    """
    Class representing a condition that must hold for labels on a PR
    """

    def __init__(self, wait_type: WaitType, regexp: str) -> None:
        self.wait_type = wait_type
        self.regexp = regexp
        self.pattern = re.compile(regexp)

    def holds(self, labels: list[str]) -> bool:
        """
        Decide whether waiting conditions hold for PR labels
        """
        if self.wait_type == WaitType.WAIT_ANY:
            return any(self.pattern.fullmatch(label) for label in labels)

        if self.wait_type == WaitType.WAIT_NONE:
            return not any(self.pattern.fullmatch(label) for label in labels)
        return False

    @staticmethod
    def get_wait_conditions(args: ap.Namespace) -> list["WaitCondition"]:
        """
        Parse all required wait conditions from program args
        """
        conditions = []

        for regexp in args.any:
            conditions.append(WaitCondition(WaitType.WAIT_ANY, regexp))

        for regexp in args.none:
            conditions.append(WaitCondition(WaitType.WAIT_NONE, regexp))

        return conditions

    def __eq__(self, __value: object) -> bool:  # pragma: nocover
        if not isinstance(__value, WaitCondition):
            return False

        return self.wait_type == __value.wait_type and self.regexp == __value.regexp

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.wait_type}, {self.regexp})"


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

    parser.add_argument(
        "--timeout", type=int, default=60, help="Timeout for waiting in seconds."
    )

    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Interval between requests in seconds",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

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
        sys.exit(1)

    label_names = [label.name for label in pull_request.labels]

    return label_names


def wait_on_pr_labels(
    repository: Repository,
    pull_request_id: int,
    wait_conditions: list[WaitCondition],
    timeout_s: int,
    poll_interval_s: float,
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
    assert (
        poll_interval_s < timeout_s
    ), "Timeout needs to be bigger than the poll interval"

    LOGGER.debug("Waiting for %s on PR #%s", wait_conditions, pull_request_id)
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout_s:
        pr_labels = get_pr_labels(repository, pull_request_id)

        if all(condition.holds(pr_labels) for condition in wait_conditions):
            for label in pr_labels:
                print(label)

            return True

        time.sleep(poll_interval_s)

    LOGGER.debug("Timed out!")
    return False


def main() -> int:
    """
    Main function
    """
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    github_auth = Auth.Token(os.environ["GITHUB_TOKEN"])
    github = Github(auth=github_auth)

    repo_url, pull_request_id = parse_github_issue_url(args.pull_request_url)

    try:
        repository = github.get_repo(repo_url)
    except GithubException as exc:
        LOGGER.error("Unable to get repository from GitHub: %s", str(exc))
        return 2

    conditions = WaitCondition.get_wait_conditions(args)
    if not wait_on_pr_labels(
        repository,
        pull_request_id,
        conditions,
        args.timeout,
        args.poll_interval,
    ):
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
