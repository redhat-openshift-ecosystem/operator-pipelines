"""Static test for operator bundle."""

import argparse
import json
import logging
from typing import Any, Dict, List, Optional

from operator_repo import Repo, OperatorCatalogList
from operator_repo.checks import Fail, run_suite
from operatorcert.logger import setup_logger
from operatorcert.utils import SplitArgs

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Run static tests on an operator bundle"
    )
    parser.add_argument(
        "--repo-path",
        help="Path to the root of the local clone of the repo",
        required=True,
    )
    parser.add_argument(
        "--output-file", help="Path to a json file where results will be stored"
    )
    parser.add_argument(
        "--suites",
        help="A comma separated list of names of the test suites to run",
        action=SplitArgs,
        default=[
            "operatorcert.static_tests.community",
            "operatorcert.static_tests.common",
        ],
    )
    parser.add_argument(
        "--skip-tests",
        help="Ignore specific checks. Comma separated list of test names.",
        default=[],
        action=SplitArgs,
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("operator")
    parser.add_argument("bundle")
    parser.add_argument("affected_catalogs")

    return parser


def execute_checks(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    repo_path: str,
    operator_name: str,
    bundle_version: str,
    affected_catalogs: str,
    suite_names: List[str],
    skip_tests: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run a check suite against the given target and return warnings and
    failures in a format inspired by the operator-sdk bundle validate
    tool's JSON output format

    Args:
        repo_path (str): path to the root of the operator repository
        operator_name (str): name of the operator
        bundle_version (str): version of the bundle to check
        affected_catalogs (str): Coma separated list of affected catalogs
        suite_name (str): name of the suite to use
        skip_tests (Optional[List]): List of checks to skip

    Returns:
        The results of the checks in the suite applied to the given bundle
    """
    repo = Repo(repo_path)
    operator = repo.operator(operator_name)
    bundle = operator.bundle(bundle_version) if bundle_version else None
    # use operator-operator_catalogs edge to filter out deleted catalogs
    operator_catalogs = OperatorCatalogList(
        [
            catalog
            for catalog in operator.all_operator_catalogs()
            if catalog in affected_catalogs.split(",")
        ]
        if affected_catalogs
        else []
    )

    outputs = []
    passed = True

    for suite_name in suite_names:
        for result in run_suite(
            [obj for obj in (bundle, operator, operator_catalogs) if obj],
            suite_name,
            skip_tests=skip_tests,
        ):
            if isinstance(result, Fail):
                passed = False
            item = {
                "type": "error" if isinstance(result, Fail) else "warning",
                "message": result.reason,
                "test_suite": suite_name,
            }
            if result.check:
                item["check"] = result.check
            outputs.append(item)

    return {"passed": passed, "outputs": outputs}


def main() -> None:
    """
    Main function for static test runner
    """
    # Args
    parser = setup_argparser()
    args = parser.parse_args()

    # logging
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    # Logic
    result = execute_checks(
        args.repo_path,
        args.operator,
        args.bundle,
        args.affected_catalogs,
        args.suites,
        args.skip_tests,
    )

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as output_file:
            json.dump(result, output_file)
    else:
        print(json.dumps(result))


if __name__ == "__main__":  # pragma: no cover
    main()
