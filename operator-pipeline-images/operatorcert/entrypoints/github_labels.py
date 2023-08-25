"""
Script for editing a labels in a pull request.
"""
import argparse
import logging
import os
import urllib.parse
from typing import List

from github import Auth, Github, Label, PullRequest
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Github cli tool to manage labels to PR."
    )
    parser.add_argument(
        "--github-host-url",
        default="https://api.github.com",
        help="The GitHub host, default: https://api.github.com",
    )
    parser.add_argument(
        "--add-labels",
        nargs="+",
        default=[],
        help="List of labels that will be added to a pull request.",
    )
    parser.add_argument(
        "--remove-labels",
        nargs="+",
        default=[],
        help="List of labels that will be removed from a pull request.",
    )
    parser.add_argument(
        "--remove-matching-namespace-labels",
        action="store_true",
        help="A flag that enables removal of existing labels with matching "
        "namespace. The namespace is parsed from --add-labels.",
    )
    parser.add_argument(
        "--pull-request-url",
        required=True,
        help="The GitHub pull request URL where we want to edit labels.",
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def add_labels_to_pull_request(
    pull_request: PullRequest.PullRequest, label_names: List[str]
) -> None:
    """
    Add labels to a pull request.

    Args:
        pull_request (PullRequest.PullRequest): Github Pull Request object
        label_names (List[str]): List of label names to add
    """
    for label in label_names:
        LOGGER.info(f"Adding label {label}")
        pull_request.add_to_labels(label)


def remove_labels_from_pull_request(
    pull_request: PullRequest.PullRequest, label_names: List[str]
) -> None:
    """
    Remove labels from a pull request.

    Args:
        pull_request (PullRequest.PullRequest): Github Pull Request object
        label_names (List[str]):List of label names to remove
    """
    for label in label_names:
        LOGGER.info(f"Removing label {label}")
        pull_request.remove_from_labels(label)


def detect_namespace_labels(
    current_labels: List[Label.Label], label_namespaces: List[str]
) -> List[str]:
    """
    Return a list of current labels that match the given namespaces.

    Args:
        current_labels (List[Label.Label]): List of current labels
        label_namespaces (List[str]): List of label namespaces

    Returns:
        List[str]: List of current labels that match the given namespaces
    """
    namespace_labels = []
    for label in current_labels:
        for label_namespace in label_namespaces:
            if label.name.startswith(label_namespace) and "/" in label.name:
                namespace_labels.append(label.name)
    return namespace_labels


def parse_github_issue_url(github_issue_url: str) -> tuple[str, int]:
    """
    Parse github issue url and return repository and issue id.

    Args:
        github_issue_url (str): Github issue url

    Returns:
        str: Repository name
        int: Issue id
    """
    split_url = urllib.parse.urlparse(github_issue_url).path.split("/")
    repository = "/".join(split_url[1:3])
    issue_id = int(split_url[-1])
    return repository, issue_id


def add_or_remove_labels(
    github_client: Github,
    github_issue_url: str,
    add_labels: List[str],
    remove_labels: List[str],
    remove_matching_namespace_labels: bool,
) -> None:
    """
    Edit labels on a pull request based on input arguments.

    Args:
        github_client (Github): Github api client
        github_issue_url (str): Github issue url
        add_labels (List[str]): List of labels to add
        remove_labels (List[str]): List of labels to remove
        remove_matching_namespace_labels (bool): A flag that enables
            removal of existing labels within a namespace given
            by add_labels argument
    """
    repository, pr_id = parse_github_issue_url(github_issue_url)

    LOGGER.info(f"Adding labels {add_labels} to {repository}")
    repository = github_client.get_repo(repository)
    pull_request = repository.get_pull(pr_id)
    current_labels = pull_request.get_labels()

    labels_to_add = []
    labels_to_remove = []

    current_labels_name = [label.name for label in current_labels]

    for label in add_labels:
        if label not in current_labels_name:
            labels_to_add.append(label)

    for label in remove_labels:
        if label in current_labels_name:
            labels_to_remove.append(label)

    if remove_matching_namespace_labels:
        # Check if labels that will be added contains a namespace and
        # remove existing labels with matching namespace
        namespaces = []
        for label in add_labels:
            if "/" in label:
                # Parse namespace from the "add" label list
                namespaces.append(label.split("/")[0])

        # Find out which labels to remove based on the namespace
        namespace_labels = detect_namespace_labels(current_labels, namespaces)

        # Exclude labels that are already in the "add" list
        labels_to_remove_in_namespace = list(set(namespace_labels) - set(add_labels))
        LOGGER.info(f"Labels to remove in namespace: {labels_to_remove_in_namespace}")
        labels_to_remove.extend(labels_to_remove_in_namespace)

    LOGGER.info(f"Current labels: {current_labels}")
    LOGGER.info(f"Labels to add: {labels_to_add}")
    LOGGER.info(f"Labels to remove: {labels_to_remove}")

    add_labels_to_pull_request(pull_request, labels_to_add)
    remove_labels_from_pull_request(pull_request, labels_to_remove)


def main() -> None:
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    github_auth = Auth.Token(os.environ.get("GITHUB_TOKEN"))
    github = Github(auth=github_auth)

    add_or_remove_labels(
        github,
        args.pull_request_url,
        args.add_labels,
        args.remove_labels,
        args.remove_matching_namespace_labels,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
