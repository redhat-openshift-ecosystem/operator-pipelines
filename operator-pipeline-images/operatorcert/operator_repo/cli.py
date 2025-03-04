#!/usr/bin/env python3
"""
CLI tool to handle operator repositories
"""

import argparse
import logging
import sys
from collections.abc import Iterator
from itertools import chain
from pathlib import Path
from typing import Optional, Union

from .checks import get_checks, run_suite
from .core import Bundle, Operator, Repo
from .exceptions import OperatorRepoException


def parse_target(repo: Repo, target: str) -> Union[Operator, Bundle]:
    """
    Parse a target string and return the corresponding object

    Args:
        repo (Repo): Operator repository objects
        target (str): A string representing an operator or bundle

    Returns:
        Union[Operator, Bundle]: An operator or bundle object given the target string
    """
    if "/" in target:
        operator_name, operator_version = target.split("/", 1)
        return repo.operator(operator_name).bundle(operator_version)
    return repo.operator(target)


def indent(depth: int) -> str:
    """
    Indentation helper

    Args:
        depth (int): A depth level of the indentation

    Returns:
        str: An indentation string
    """
    return "  " * depth


def show_repo(repo: Repo, recursive: bool = False, depth: int = 0) -> None:
    """
    Show the contents of the repository

    Args:
        repo (Repo): An instance of the Repo class
        recursive (bool, optional): A flag determins if a print goes to deeper level.
        Defaults to False.
        depth (int, optional): A current recusion depth. Defaults to 0.
    """
    print(indent(depth) + str(repo))
    for operator in repo:
        if recursive:
            show_operator(operator, recursive, depth + 1)
        else:
            print(indent(depth + 1) + str(operator))


def show_operator(operator: Operator, recursive: bool = False, depth: int = 0) -> None:
    """
    Show the contents of the operator

    Args:
        operator (Operator): An instance of the Operator class
        recursive (bool, optional): A flag determins if a print goes to deeper level.
        Defaults to False.
        depth (int, optional): A current recusion depth. Defaults to 0.
    """
    print(indent(depth) + str(operator))
    for bundle in operator:
        if recursive:
            show_bundle(bundle, depth + 1)
        else:
            print(indent(depth + 1) + str(bundle))
    # list also the operator catalogs if exist
    for operator_catalog in operator.all_operator_catalogs():
        print(indent(depth + 1) + str(operator_catalog))


def show_bundle(bundle: Bundle, depth: int = 0) -> None:
    """
    Show the contents of the bundle

    Args:
        bundle (Bundle): An instance of the Bundle class
        depth (int, optional): A current recusion depth. Defaults to 0.
    """
    print(indent(depth) + str(bundle))
    csv_annotations = bundle.csv.get("metadata", {}).get("annotations", {})
    info = [
        ("Description", csv_annotations.get("description", "")),
        ("Name", f"{bundle.csv_operator_name}.v{bundle.csv_operator_version}"),
        ("Channels", ", ".join(bundle.channels)),
        ("Default channel", bundle.default_channel),
        ("Container image", csv_annotations.get("containerImage", "")),
        ("Replaces", bundle.csv.get("spec", {}).get("replaces", "")),
        ("Skips", bundle.csv.get("spec", {}).get("skips", [])),
    ]
    max_width = max(len(key) for key, _ in info)
    for key, value in info:
        message = f"{key.ljust(max_width + 1)}: {value}"
        print(indent(depth + 1) + message)


def show(target: Union[Repo, Operator, Bundle], recursive: bool = False) -> None:
    """
    Show the contents of the target

    Args:
        target (Union[Repo, Operator, Bundle]): An instance of the Repo, Operator
        or Bundle class
        recursive (bool, optional): A recusive flag. Defaults to False.
    """
    if isinstance(target, Repo):
        show_repo(target, recursive, 0)
    elif isinstance(target, Operator):
        show_operator(target, recursive, 1 * recursive)
    elif isinstance(target, Bundle):
        show_bundle(target, 2 * recursive)


def action_list(repo: Repo, *what: str, recursive: bool = False) -> None:
    """
    List the contents of the repository

    Args:
        repo (Repo): An instance of the Repo class
        what (str): A list of names of the operators or bundles to list
        recursive (bool, optional): A recursion flag. Defaults to False.
    """
    if what:
        targets: Iterator[Union[Repo, Operator, Bundle]] = (
            parse_target(repo, x) for x in what
        )
    else:
        targets = iter([repo])
    for target in targets:
        show(target, recursive)


def _walk(target: Union[Operator, Bundle]) -> Iterator[Union[Operator, Bundle]]:
    """
    Walk through the target and yield all operators and bundles

    Args:
        target (Union[Operator, Bundle]): An instance of the Operator or Bundle class

    Yields:
        Iterator[Union[Operator, Bundle]]: An operator or bundle object
    """
    yield target
    if isinstance(target, Operator):
        yield from target.all_bundles()


def action_check(repo: Repo, suite: str, *what: str, recursive: bool = False) -> None:
    """
    Check the validity of the operators or bundles

    Args:
        repo (Repo): An instance of the Repo class
        suite (str): A path to the check suite
        recursive (bool, optional): Recusion flag. Defaults to False.
    """
    if what:
        targets: Iterator[Union[Operator, Bundle]] = (
            parse_target(repo, x) for x in what
        )
    else:
        targets = repo.all_operators()
    if recursive:
        all_targets: Iterator[Union[Operator, Bundle]] = chain.from_iterable(
            _walk(x) for x in targets
        )
    else:
        all_targets = targets
    for result in run_suite(all_targets, suite_name=suite):
        print(result)


def action_check_list(suite: str) -> None:
    """
    List available checks

    Args:
        suite (str): A path to the check suite
    """
    for check_type_name, checks in get_checks(suite).items():
        print(f"{check_type_name} checks:")
        for check in checks:
            display_name = check.__name__.removeprefix("check_")
            print(f" - {display_name}: {check.__doc__}")


def _get_repo(path: Optional[Path] = None) -> Repo:
    """
    Get an instance of the Repo class from the given path

    Args:
        path (Optional[Path], optional): A local path to repository. Defaults to None.

    Returns:
        Repo: A Repo object
    """
    if not path:
        path = Path.cwd()
    try:
        return Repo(path)
    except OperatorRepoException:
        print(f"{path} is not a valid operator repository")
        sys.exit(1)


def main() -> None:
    """
    Main function for the CLI tool
    """
    main_parser = argparse.ArgumentParser(
        description="Operator repository manipulation tool",
    )
    main_parser.add_argument(
        "-r", "--repo", help="path to the root of the operator repository", type=Path
    )
    main_parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="increase log verbosity"
    )
    main_subparsers = main_parser.add_subparsers(dest="action")

    # list
    list_parser = main_subparsers.add_parser(
        "list", aliases=["ls"], help="list contents of repo, operators or bundles"
    )
    list_parser.add_argument(
        "-R", "--recursive", action="store_true", help="descend the tree"
    )
    list_parser.add_argument(
        "target",
        nargs="*",
        help="name of the repos or bundles to list; if omitted, list the contents of the repo",
    )

    # check_bundle
    check_parser = main_subparsers.add_parser(
        "check",
        help="check validity of an operator or bundle",
    )
    check_parser.add_argument(
        "-s",
        "--suite",
        default="operatorcert.static_tests.common",
        help="check suite to use",
    )
    check_parser.add_argument(
        "-l", "--list", action="store_true", help="list available checks"
    )
    check_parser.add_argument(
        "-R", "--recursive", action="store_true", help="descend the tree"
    )
    check_parser.add_argument(
        "target",
        nargs="*",
        help="name of the operators or bundles to check",
    )

    args = main_parser.parse_args()

    verbosity = {0: logging.ERROR, 1: logging.WARNING, 2: logging.INFO}
    log = logging.getLogger(__package__)
    log.setLevel(verbosity.get(args.verbose, logging.DEBUG))
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
    )
    log.addHandler(handler)

    if args.action in ("list", "ls"):
        action_list(_get_repo(args.repo), *args.target, recursive=args.recursive)
    elif args.action == "check":
        if args.list:
            action_check_list(args.suite)
        else:
            action_check(
                _get_repo(args.repo),
                args.suite,
                *args.target,
                recursive=args.recursive,
            )
    else:
        main_parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    main()
