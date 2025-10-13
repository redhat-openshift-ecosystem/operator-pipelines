"""
Generate a summary comment based on various category checkers and post it to Slack.
"""

import datetime
import logging
import os
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote_plus

import requests
from github import Github
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")

COMMUNITY_OCP_REPO = "redhat-openshift-ecosystem/community-operators-prod"
COMMUNITY_K8S_REPO = "k8s-operatorhub/community-operators"

EXCLUDE_FILTER = "-label:report/skip"

GITHUB_BASE_URL = "https://github.com"

ISSUE_DISPLAY_LIMIT = int(
    os.environ.get("ISSUE_DISPLAY_LIMIT", "5")
)  # Max number of issues to display in the summary


class CategorySummary:  # pylint: disable=too-few-public-methods
    """
    Represents the structured result of a category check.
    """

    def __init__(
        self,
        category: str,
        items: list[Any],
        summary_text: str,
        instructions: str = "",
    ):
        self.category = category
        self.items = items  # structured data (e.g. PRs, issues, etc.)
        self.summary_text = summary_text  # human-readable summary
        self.instructions = instructions  # action items or next steps

    def __str__(self) -> str:
        if len(self.items) == 0:
            return f"📌 *{self.category.capitalize()}*\n{self.summary_text}"
        return (
            f"📌 *{self.category.capitalize()}*\n{self.summary_text}\n"
            f"*Instructions:* {self.instructions}"
        )


class SummaryAggregator:  # pylint: disable=too-few-public-methods
    """
    Combines multiple CategorySummaries into one report.
    """

    def __init__(self, summaries: list[CategorySummary]):
        self.summaries = summaries

    def generate_report(self) -> str:
        """
        Generate a consolidated report from all category summaries.

        Returns:
            str: A formatted report string.
        """
        today = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
        separator = "-" * 80
        header = f"*Daily Support Summary – {today}*\n\n"
        body = f"\n{separator}\n\n".join(str(s) for s in self.summaries)
        return header + body


class CategoryChecker(ABC):  # pragma: no cover
    """
    Abstract base class for all category checkers.
    """

    def __init__(self, github_client: Github, repos: list[str]):
        self.github_client = github_client
        self.repos = repos

    category_name: str

    @abstractmethod
    def run(self) -> CategorySummary:
        """
        Execute the check and return a CategorySummary.
        """

    @property
    def query(self) -> str:
        """
        A GitHub search query to find relevant issues or PRs.

        Returns:
            str: A GitHub search query string.
        """
        return ""

    @property
    def repo_query(self) -> str:
        """
        A GitHub search query to find relevant issues or PRs for a single repo.

        Returns:
            str: A GitHub search query string.
        """
        return " ".join(f"repo:{repo}" for repo in self.repos)

    @property
    def github_link(self) -> str:
        """
        A direct link to the GitHub search results for the query.

        Returns:
            str: A URL string.
        """
        if len(self.repos) > 1:
            return f"{GITHUB_BASE_URL}/search?q={quote_plus(self.query)}"
        return f"{GITHUB_BASE_URL}/{self.repos[0]}/pulls?q={quote_plus(self.query)}"

    def to_summary_text(
        self, items: Any, no_items_text: str, many_items_text: str
    ) -> str:
        """
        Convert a list of items into a summary text based on the number of items.
        In case of many items, provide a link to GitHub instead of listing them all.

        Args:
            items (Any): A list of items (e.g., PRs, issues).
            no_items_text (str): A summary text when there are no items.
            many_items_text (str): A summary text format when there are many items.

        Returns:
            str: A summary text.
        """
        if not items:
            return no_items_text
        if len(items) > ISSUE_DISPLAY_LIMIT:
            return many_items_text.format(count=len(items), link=self.github_link)

        summary = f"{len(items)} item(s):\n```\n"
        for item in items:
            summary += f"• <{item.html_url}|{item.title}>\n"
        summary += "```"
        return summary


class OCPPullRequestReview(CategoryChecker):
    """
    Checker for the open OCP community PRs needing review.
    """

    category_name = "OpenShift Community PRs Needing Review"
    instructions = (
        "Check if a PR doesn't contain any inappropriate language or something "
        "that should not be merged. If not, merge the PR."
    )

    @property
    def query(self) -> str:
        """
        A GitHub search query to find relevant issues or PRs.

        Returns:
            str: A GitHub search query string.
        """
        return (
            f"{self.repo_query} is:pr is:open label:operator-hosted-pipeline/passed "
            f"{EXCLUDE_FILTER}"
        )

    def run(self) -> CategorySummary:
        """
        Find PRs needing review and generate a summary.

        Returns:
            CategorySummary: A summary of PRs needing review.
        """
        LOGGER.debug("OCP PRs needing review query: %s", self.query)
        prs_needing_review = list(self.github_client.search_issues(self.query))

        summary_text = self.to_summary_text(
            prs_needing_review,
            "No PRs waiting for review 🎉",
            "*{count}* PRs waiting for review. See all at <{link}|Github>",
        )

        return CategorySummary(
            self.category_name, prs_needing_review, summary_text, self.instructions
        )


class OCPFailedReleasePipeline(CategoryChecker):
    """
    Checker for the OCP community PRs with failed release pipelines.
    """

    category_name = "Failed Release Pipelines"
    instructions = (
        "Check a rootcause of the pipeline. In case of temporary failure, restart "
        "the pipeline by adding `pipeline/trigger-release` label. Otherwise "
        "create a ticket in our backlog and bring the issue to a team."
    )

    @property
    def query(self) -> str:
        """
        A GitHub search query to find relevant issues or PRs.

        Returns:
            str: A GitHub search query string.
        """
        return (
            f"{self.repo_query} is:pr label:operator-release-pipeline/failed is:closed "
            f"{EXCLUDE_FILTER}"
        )

    def run(self) -> CategorySummary:
        """
        Find PRs with failed release pipelines and generate a summary.

        Returns:
            CategorySummary: A summary of PRs with failed release pipelines.
        """
        LOGGER.debug("OCP Failed Release Pipeline query: %s", self.query)
        prs_needing_review = list(self.github_client.search_issues(self.query))

        summary_text = self.to_summary_text(
            prs_needing_review,
            "No PRs with failed release pipeline 🎉",
            "*{count}* PR(s) waiting for investigation. See all at <{link}|Github>",
        )

        return CategorySummary(
            self.category_name, prs_needing_review, summary_text, self.instructions
        )


class OCPFailedHostedPipeline(CategoryChecker):
    """
    Checker for the OCP community PRs with failed hosted pipelines.
    """

    category_name = "Failed Hosted Pipelines"
    instructions = (
        "Check a rootcause of the failed pipeline. If an issues is caused by the"
        "operator itself, skip it. "
        "In case of temporary failure, restart the pipeline by adding "
        "`pipeline/trigger-hosted` label. Otherwise "
        "create a ticket in our backlog and bring the issue to a team."
    )

    @property
    def query(self) -> str:
        """
        A GitHub search query to find relevant issues or PRs.

        Returns:
            str: A GitHub search query string.
        """
        return (
            f"{self.repo_query} is:pr is:open label:operator-hosted-pipeline/failed "
            f"{EXCLUDE_FILTER}"
        )

    def run(self) -> CategorySummary:
        """
        Find PRs with failed release pipelines and generate a summary.

        Returns:
            CategorySummary: A summary of PRs with failed release pipelines.
        """
        LOGGER.debug("OCP Failed Hosted Pipeline query: %s", self.query)
        prs_needing_review = list(self.github_client.search_issues(self.query))

        summary_text = self.to_summary_text(
            prs_needing_review,
            "No PRs with failed hosted pipeline 🎉",
            "*{count}* PR(s) waiting for investigation. See all at <{link}|Github>",
        )

        return CategorySummary(
            self.category_name, prs_needing_review, summary_text, self.instructions
        )


class K8sPullRequestReview(CategoryChecker):
    """
    Checker for the open K8s community PRs needing review.
    """

    category_name = "K8s Community PRs Needing Review"
    instructions = (
        "Check in the PR comments if a PR is waiting for a operator "
        "owner review. If so, wait till they provide the review. "
        "Otherwise check if a PR doesn't contain any inappropriate "
        "language or something that should not be merged. If not, "
        "add authorized-changes label to the PR. The PR gets merged automatically."
    )

    @property
    def query(self) -> str:
        """
        A GitHub search query to find relevant issues or PRs.

        Returns:
            str: A GitHub search query string.
        """
        return (
            f"{self.repo_query} is:pr -label:authorized-changes is:open status:success "
            f"{EXCLUDE_FILTER}"
        )

    def run(self) -> CategorySummary:
        """
        Find PRs needing review and generate a summary.

        Returns:
            CategorySummary: A summary of PRs needing review.
        """
        LOGGER.debug("K8s PRs needing review query: %s", self.query)
        prs_needing_review = list(self.github_client.search_issues(self.query))

        summary_text = self.to_summary_text(
            prs_needing_review,
            "No PRs waiting for review 🎉",
            "*{count}* PRs waiting for review. See all at <{link}|Github>",
        )

        return CategorySummary(
            self.category_name, prs_needing_review, summary_text, self.instructions
        )


class NewIssues(CategoryChecker):
    """
    Checker for new issues created in the last 7 days in the OCP and K8s community repos.
    """

    category_name = "Operator repositories - New Issues (last 7 days)"
    instructions = (
        "Check if a new issue was created by a user that needs help. If so, "
        "provide help or bring the issue to a team."
    )

    @property
    def query(self) -> str:
        """
        A GitHub search query to find relevant issues or PRs.

        Returns:
            str: A GitHub search query string.
        """
        return (
            self.repo_query
            + " is:issue created:>="
            + str(date.today() - timedelta(days=7))
            + f" {EXCLUDE_FILTER}"
        )

    @property
    def github_link(self) -> str:
        """
        A direct link to the GitHub search results for the query.

        Returns:
            str: A URL string.
        """
        return f"{GITHUB_BASE_URL}/search?q={quote_plus(self.query)}"

    def run(self) -> CategorySummary:
        """
        Find a new issues and generate a summary.

        Returns:
            CategorySummary: A summary of new issues.
        """
        LOGGER.debug("New issues query: %s", self.query)
        prs_needing_review = list(self.github_client.search_issues(self.query))

        summary_text = self.to_summary_text(
            prs_needing_review,
            "No new Issues waiting for review 🎉",
            "*{count}* new Issues waiting for review. See all at <{link}|Github>",
        )

        return CategorySummary(
            self.category_name, prs_needing_review, summary_text, self.instructions
        )


class Misc(CategoryChecker):
    """
    Miscellaneous category with general instructions.
    """

    category_name = "Miscellaneous"
    instructions = "No action needed."

    def __init__(self, github_client: Github):
        super().__init__(github_client, [])

    def run(self) -> CategorySummary:
        summary_text = (
            "Keep an eye on Slack channels <#C01UYB5E414> and <#C06LTFLUQMQ>\n"
            " • Check if there are any urgent issues or PRs that need attention.\n"
            " • In the slack threads, to notify that you are taking a look at an alert, "
            "please react with :eyes: or let the rest know that you are into it by adding "
            "a comment in the channel or any other informative way that you prefer.\n"
        )
        return CategorySummary(self.category_name, [], summary_text, self.instructions)


def generate_summary_comment(gh_client: Github) -> None:
    """
    Generate a summary comment based on various category checkers and post it to Slack.

    Args:
        gh_client (Github): A GitHub client instance.
    """
    categories = [
        OCPPullRequestReview(gh_client, [COMMUNITY_OCP_REPO]),
        OCPFailedReleasePipeline(gh_client, [COMMUNITY_OCP_REPO]),
        OCPFailedHostedPipeline(gh_client, [COMMUNITY_OCP_REPO]),
        K8sPullRequestReview(gh_client, [COMMUNITY_K8S_REPO]),
        NewIssues(gh_client, [COMMUNITY_OCP_REPO, COMMUNITY_K8S_REPO]),
        Misc(gh_client),
    ]
    summaries = []
    for category in categories:
        summary = category.run()
        summaries.append(summary)

    aggregator = SummaryAggregator(summaries)
    report = aggregator.generate_report()
    LOGGER.info("Generated report:\n%s", report)

    slack_webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    resp = requests.post(slack_webhook_url, json={"text": report}, timeout=10)
    resp.raise_for_status()


def main() -> None:
    """
    Main entry point for the support summary script.
    """
    setup_logger("DEBUG")

    gh_client = Github(os.environ["GITHUB_TOKEN"])
    generate_summary_comment(gh_client)


if __name__ == "__main__":  # pragma: no cover
    main()
