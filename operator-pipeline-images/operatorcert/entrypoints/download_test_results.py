"""Download the test results and logs from the CI pipeline."""
import argparse

from operatorcert import download_test_results
from operatorcert.logger import setup_logger
from operatorcert.utils import store_results


def setup_argparser() -> argparse.ArgumentParser:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        argparse.ArgumentParser: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Get the test results and logs from the CI pipeline."
        "Test results can be found in the file test_results.json"
    )
    parser.add_argument(
        "--pyxis-url",
        default="https://pyxis.engineering.redhat.com",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument(
        "--cert-project-id", help="Certification project ID", required=True
    )
    parser.add_argument(
        "--certification-hash", help="Certification bundle hash", required=True
    )
    parser.add_argument("--operator-name", help="Operator name", required=True)
    parser.add_argument(
        "--operator-package-version", help="Operator package version", required=True
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def main() -> None:
    """
    Download the test results and logs from the CI pipeline.
    """
    # Args
    parser = setup_argparser()
    args = parser.parse_args()

    # Logging
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    # Logic
    test_results_id = download_test_results(args)

    # Store results
    store_results({"test_result_id": test_results_id})


if __name__ == "__main__":  # pragma: no cover
    main()
