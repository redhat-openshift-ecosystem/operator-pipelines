"""Parse and filter preflight results for community."""
import argparse
import json
import logging
from typing import Any, Dict

from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")

COMMUNITY_ALLOWED_TESTS = [
    "ScorecardBasicSpecCheck",
    "ScorecardOlmSuiteCheck",
    "DeployableByOLM",
]


def setup_argparser() -> Any:
    """
    Create an argument parser.

    Returns:
        Any: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Parse and filter preflight results for community."
    )
    parser.add_argument("--test-results", help="Path to a preflight test-results.")
    parser.add_argument("--output-file", help="Place to write the filtered results.")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def is_allowed_test(test: Any) -> bool:
    """
    Check if the test is allowed for community.

    Args:
        test (Any): Test object

    Returns:
        bool: True if the test is allowed, False otherwise
    """
    test_name = test.get("name")
    allowed = test_name in COMMUNITY_ALLOWED_TESTS
    if not allowed:
        LOGGER.debug("Skipping test: %s", test_name)
    LOGGER.info("Test: %s, allowed: %s", test_name, allowed)
    return allowed


def parse_and_evaluate_results(test_results: Any) -> Any:
    """
    Parse a preflight test-results and filter out tests that are not
    allowed for community.

    Args:
        test_results (Any): Preflight test-results object

    Returns:
        Any: A filtered preflight test-results object
    """
    new_results: Dict[str, Any] = {}
    results = test_results.get("results", {})
    for category, tests in results.items():
        new_results[category] = []
        for test in tests:
            if is_allowed_test(test):
                new_results[category].append(test)

    overall_status = True
    if new_results.get("errors") or new_results.get("failed"):
        overall_status = False

    LOGGER.info("Overall status: %s", overall_status)
    result_by_category = {
        category: len(tests) for category, tests in new_results.items()
    }

    LOGGER.info("Result by category: %s", result_by_category)

    test_results["results"] = new_results
    test_results["passed"] = overall_status

    return test_results


def main() -> None:
    """
    Parse and filter preflight results for community.
    """
    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)

    with open(args.test_results, "r", encoding="utf-8") as test_results:
        test_results = json.load(test_results)
    community_results = parse_and_evaluate_results(test_results)

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as output_file:
            json.dump(community_results, output_file, indent=2)


if __name__ == "__main__":  # pragma: no cover
    main()
