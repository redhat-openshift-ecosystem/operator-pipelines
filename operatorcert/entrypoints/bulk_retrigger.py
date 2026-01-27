#!/usr/bin/env python3
"""
Perform bulk re-triggering of an operator pipeline on a given list of PRs.

The re-triggering of the pipeline against a PR is performed by applying the
appropriate label to the PR and waiting for the pipeline to apply a success
or failure label.

The list of PRs to process must be provided in CSV format. PRs are processed
one at a time in the order they appear in the CSV file.
"""

import argparse
import csv
import logging
import os
from pathlib import Path
import sys
import time
from typing import Optional, Iterator

from github import Github, Auth
from github.Repository import Repository
from github.PullRequest import PullRequest

logger = logging.getLogger(__name__)


class CSVNotFound(Exception):
    """Exception raised when the specified CSV file is not found."""


class MissingToken(Exception):
    """Exception raised when the GitHub token is not set in the environment."""


class InvalidRepoName(Exception):
    """Exception raised when the provided repository name is invalid."""


def wait_for_all_labels(
    pr: PullRequest,
    present: Optional[set[str]] = None,
    absent: Optional[set[str]] = None,
    poll_interval: float = 15.0,
    retries: int = 20,
) -> bool:
    """
    Wait for all specified labels to be present and absent on a pull request.

    Args:
        pr (PullRequest): The pull request to check labels on.
        present (Optional[set[str]]): A set of labels that must be present.
        absent (Optional[set[str]]): A set of labels that must be absent.
        poll_interval (float): Time to wait between checks (in seconds).
        retries (int): Number of times to check for the labels.

    Returns:
        bool: True if the required labels are present and absent, False otherwise.
    """

    if present is None:
        present = set()
    if absent is None:
        absent = set()
    for t in range(retries):
        time.sleep(poll_interval)
        logger.debug(
            "Checking if PR %d has all labels: present=%s absent=%s (%d/%d)",
            pr.number,
            present,
            absent,
            t + 1,
            retries,
        )
        labels = {x.name for x in pr.get_labels()}
        if present.issubset(labels) and not absent.intersection(labels):
            return True
    logger.debug("Exceeded maximum retries")
    return False


def wait_for_any_label(
    pr: PullRequest,
    present: Optional[set[str]] = None,
    poll_interval: float = 15.0,
    retries: int = 20,
) -> bool:
    """
    Wait for any of the specified labels to be present on a pull request.

    Args:
        pr (PullRequest): The pull request to check labels on.
        present (Optional[set[str]]): A set of labels to check for presence.
        poll_interval (float): Time to wait between checks (in seconds).
        retries (int): Number of times to check for the labels.

    Returns:
        bool: True if any of the specified labels are present, False otherwise.
    """

    if present is None:
        present = set()
    if not present:
        return True
    for t in range(retries):
        logger.debug(
            "Checking if PR %d has any label: present=%s (%d/%d)",
            pr.number,
            present,
            t + 1,
            retries,
        )
        time.sleep(poll_interval)
        labels = {x.name for x in pr.get_labels()}
        if present.intersection(labels):
            return True
    logger.debug("Exceeded maximum retries")
    return False


def parse_repo_name(repo_name: str) -> Repository:
    """
    Parse the repository name and return the corresponding GitHub Repository object.

    Args:
        repo_name (str): The repository name in the format 'namespace/repo_name' or a full URL.

    Returns:
        Repository: The GitHub Repository object.

    Raises:
        MissingToken: If the GitHub token is not set in the environment.
        InvalidRepoName: If the provided repository name is invalid.
    """

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.critical("GITHUB_TOKEN not set")
        raise MissingToken()
    gh = Github(auth=Auth.Token(token))
    if repo_name.startswith("https://") or repo_name.startswith("http://"):
        if repo_name.startswith("https://github.com/"):
            repo_name = repo_name.removeprefix("https://github.com/")
        else:
            logger.critical("%s does not look like a GitHup repo", repo_name)
            raise InvalidRepoName()
    return gh.get_repo(repo_name)


def pr_numbers_from_csv(
    csv_file: Path, csv_delimiter: str, pr_column: int
) -> Iterator[int | Exception]:
    """
    Extract pull request numbers from a CSV file.

    Args:
        csv_file (Path): The path to the CSV file containing PR numbers.
        csv_delimiter (str): The character used to separate fields in the CSV file.
        pr_column (int): The index (zero-based) of the column in the CSV file that contains
            the PR numbers.

    Yields:
        Iterator[int | Exception]: An iterator that yields PR numbers as integers. If an error
            occurs while parsing a PR number, it yields the exception instead.

    Raises:
        CSVNotFound: If the specified CSV file does not exist.
    """

    if not csv_file.exists():
        logger.critical("CSV file %s not found", csv_file)
        raise CSVNotFound()
    with csv_file.open() as f:
        reader = csv.reader(f, delimiter=csv_delimiter)
        for line_number, row in enumerate(reader):
            try:
                yield int(row[pr_column])
            except (ValueError, KeyError) as exc:
                logger.exception("Invalid PR number at line %d", line_number)
                yield exc


def retrigger_pipeline_for_pr(
    gh_repo: Repository, pr_id: int, pipeline: str, pipeline_timeout_minutes: int
) -> str:
    """
    Re-trigger the specified pipeline for a given pull request and wait for the pipeline
    to finish.

    Args:
        gh_repo (Repository): The GitHub repository object where the pull request resides.
        pr_id (int): The ID of the pull request to re-trigger the pipeline for.
        pipeline (str): The name of the pipeline to re-trigger (e.g., "hosted" or "release").
        pipeline_timeout_minutes (int): The timeout in minutes for the pipeline run.

    Returns:
        str: The result of the pipeline re-triggering, which can be one of the following:
            - "skipped": If the pipeline was already started or triggered.
            - "timeout": If the pipeline did not finish within the specified timeout.
            - "pass": If the pipeline completed successfully.
            - "fail": If the pipeline failed.

    Raises:
        Exception: If there is an error while processing the pull request or interacting with
            the GitHub API.
    """

    logger.debug("Processing PR %d", pr_id)
    pr = gh_repo.get_pull(pr_id)
    labels = {x.name for x in pr.get_labels()}
    started_label = f"operator-{pipeline}-pipeline/started"
    passed_label = f"operator-{pipeline}-pipeline/passed"
    failed_label = f"operator-{pipeline}-pipeline/failed"
    trigger_label = f"pipeline/trigger-{pipeline}"
    if started_label in labels or trigger_label in labels:
        return "skipped"
    logger.debug("Applying label %s to PR %d", trigger_label, pr_id)
    pr.add_to_labels(trigger_label)
    # Wait for the bot to remove the trigger label
    if not wait_for_all_labels(pr, absent={trigger_label}):
        return "timeout"
    # Wait for the pipeline to finish without hammering the API
    pipeline_retries = 20
    pipeline_interval = max(
        30.0, 1.0 + pipeline_timeout_minutes * 60.0 / pipeline_retries
    )
    if not wait_for_any_label(
        pr,
        present={passed_label, failed_label},
        poll_interval=pipeline_interval,
        retries=pipeline_retries,
    ):
        return "timeout"
    labels = {x.name for x in pr.get_labels()}
    if passed_label in labels:
        return "pass"
    return "fail"


def bulk_retrigger(
    repo: Repository,
    pipeline: str,
    prs: Iterator[int | Exception],
    pipeline_timeout_minutes: int,
) -> int:
    """
    Bulk re-trigger the specified pipeline for a list of pull requests.

    Args:
        repo (Repository): The GitHub repository object where the pull requests reside.
        pipeline (str): The name of the pipeline to re-trigger (e.g., "hosted" or "release").
        prs (Iterator[int | Exception]): An iterator that yields pull request numbers or
            exceptions.
        pipeline_timeout_minutes (int): The timeout in minutes for the pipeline run.

    Returns:
        int: The number of pull requests that failed to process.

    This function processes each pull request in the provided iterator, attempting to re-trigger
    the specified pipeline. It logs the results of each operation and counts the number of
    failures encountered during the process.
    """

    logger.debug("Bulk triggering %s pipeline on GitHub repository %s", pipeline, repo)
    fail_count = 0
    for pr in prs:
        if isinstance(pr, Exception):
            fail_count += 1
            continue
        logger.info("Triggering %s pipeline for PR %d", pipeline, pr)
        try:
            result = retrigger_pipeline_for_pr(
                repo, pr, pipeline, pipeline_timeout_minutes
            )
            logger.info("Finished processing PR %d: %s", pr, result)
            if result != "pass":
                fail_count += 1
        except Exception:  # pylint: disable=broad-except
            logger.exception("Processing PR %d failed", pr)
            fail_count += 1
    logger.debug(
        "Finished triggering %s pipeline on GitHub repository %s with %d failures",
        pipeline,
        repo,
        fail_count,
    )
    return fail_count


def setup_logging(verbose: bool) -> None:
    """
    Set up the logging configuration for the application.

    Args:
        verbose (bool): If True, set the logging level to DEBUG; otherwise, set it to INFO.

    This function configures the logging format and level for the application, allowing for
    detailed debug messages when verbose mode is enabled.
    """

    logging.basicConfig(
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        level=logging.DEBUG if verbose else logging.INFO,
    )


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the bulk re-triggering script.

    Returns:
        argparse.Namespace: An object containing the parsed command-line arguments.

    This function sets up the argument parser, defines the expected arguments, and
    returns the parsed arguments as a namespace object for further processing.
    """

    parser = argparse.ArgumentParser(
        prog="bulk-retrigger",
        description=(
            "Re-trigger an operator pipeline on a list of PRs. "
            "A valid GitHub token must be provided in the GITHUB_TOKEN environment variable."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--pipeline",
        type=str,
        choices=("hosted", "release"),
        default="release",
        help="Pipeline to re-trigger",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=75,
        help="Timeout in minutes for the pipeline run",
    )
    parser.add_argument(
        "-d",
        "--csv-delimiter",
        default=",",
        help="Field separator character used in the CSV file",
    )
    parser.add_argument(
        "-c",
        "--pr-column",
        type=int,
        default=0,
        help="Index (zero-based) of the column in the CSV file containing the PR number",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug log messages"
    )
    parser.add_argument(
        "repo",
        type=str,
        help=(
            "Target GitHub repository (namespace/repo_name or "
            "https://github.com/namespace/repo_name)"
        ),
    )
    parser.add_argument(
        "csv", type=Path, help="Path to the CSV file containing the PRs to process"
    )
    return parser.parse_args()


def main() -> int:  # pragma: no cover
    """Script entry point"""

    args = parse_args()
    setup_logging(args.verbose)
    try:
        repo = parse_repo_name(args.repo)
        prs = pr_numbers_from_csv(args.csv, args.csv_delimiter, args.pr_column)
        failures = bulk_retrigger(repo, args.pipeline, prs, args.timeout)
        return 0 if failures == 0 else 1
    except CSVNotFound:
        return 2
    except MissingToken:
        return 3
    except InvalidRepoName:
        return 4


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
