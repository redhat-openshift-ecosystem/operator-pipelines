import argparse
import json
import logging
from typing import Any, Dict

from operator_repo import Repo
from operator_repo.checks import Fail, run_suite

from operatorcert.logger import setup_logger

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
        "--suite",
        help="Name of the test suite to run",
        default="operatorcert.static_tests.community",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("operator")
    parser.add_argument("bundle")

    return parser


def check_bundle(
    repo_path: str,
    operator_name: str,
    bundle_version: str,
    suite_name: str,
) -> Dict[str, Any]:
    """
    Run a check suite against the given bundle and return warnings and
    failures in a format inspired by the operator-sdk bundle validate
    tool's JSON output format

    Args:
        repo_path: path to the root of the operator repository
        operator_name: name of the operator
        bundle_version: version of the bundle to check
        suite_name: name of the suite to use

    Returns:
        The results of the checks in the suite applied to the given bundle
    """
    repo = Repo(repo_path)
    operator = repo.operator(operator_name)
    bundle = operator.bundle(bundle_version)

    outputs = []
    passed = True

    for result in run_suite([bundle, operator], suite_name):
        if isinstance(result, Fail):
            passed = False
        item = {
            "type": "error" if isinstance(result, Fail) else "warning",
            "message": result.reason,
        }
        if result.check:
            item["check"] = result.check
        outputs.append(item)

    return {"passed": passed, "outputs": outputs}


def main() -> None:
    # Args
    parser = setup_argparser()
    args = parser.parse_args()

    # logging
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    # Logic
    result = check_bundle(
        args.repo_path,
        args.operator,
        args.bundle,
        args.suite,
    )

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as output_file:
            json.dump(result, output_file)
    else:
        print(json.dumps(result))


if __name__ == "__main__":  # pragma: no cover
    main()
