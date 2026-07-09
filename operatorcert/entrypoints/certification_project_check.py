"""Check certification project identifiers for affected operators."""

import argparse
import logging
import sys
from pathlib import Path

from operatorcert.logger import setup_logger
from operatorcert.operator_repo.utils import load_yaml
from operatorcert.utils import SplitArgs

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        argparse.ArgumentParser: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Check certification project identifiers for affected operators."
    )
    parser.add_argument(
        "--repo-head-path",
        required=True,
        type=Path,
        help="Path to the PR head repository clone",
    )
    parser.add_argument(
        "--repo-base-path",
        type=Path,
        help="Path to the base branch repository clone",
    )
    parser.add_argument(
        "--affected-operators",
        default=[],
        action=SplitArgs,
        help="Comma separated list of affected operators",
    )
    parser.add_argument(
        "--affected-catalog-operators",
        default=[],
        action=SplitArgs,
        help="Comma separated list of affected catalog operators",
    )
    parser.add_argument(
        "--cert-project-required",
        default="true",
        help="Whether a cert project ID must be present",
    )
    parser.add_argument(
        "--output-file",
        help="Path to a file where the certification project ID will be stored",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def collect_affected_operators(
    affected_operators: list[str], affected_catalog_operators: list[str]
) -> set[str]:
    """
    Build a set of operator names affected by the pull request.

    Args:
        affected_operators (list[str]): Operator names from detect-changes
        affected_catalog_operators (list[str]): Catalog operators in catalog/version format

    Returns:
        set[str]: Unique affected operator names
    """
    operators = set(affected_operators)
    for catalog_operator in affected_catalog_operators:
        if not catalog_operator or "/" not in catalog_operator:
            continue
        _, operator_name = catalog_operator.split("/", 1)
        if operator_name.strip():
            operators.add(operator_name.strip())
    return operators


def resolve_operator_ci_yaml_path(
    source_root: Path,
    base_root: Path | None,
    operator_name: str,
) -> Path:
    """
    Resolve the ci.yaml path for an operator, falling back to the base branch.

    Args:
        source_root (Path): PR head repository root
        base_root (Path | None): Base branch repository root
        operator_name (str): Operator name

    Returns:
        Path: Resolved ci.yaml path

    Raises:
        FileNotFoundError: When ci.yaml cannot be found in head or base
    """
    head_path = source_root / "operators" / operator_name / "ci.yaml"
    if head_path.is_file():
        return head_path

    if base_root is not None:
        base_path = base_root / "operators" / operator_name / "ci.yaml"
        if base_path.is_file():
            LOGGER.info(
                "Using ci.yaml from base branch for operator '%s' (removed in PR).",
                operator_name,
            )
            return base_path

    raise FileNotFoundError(
        f"ci.yaml not found for operator '{operator_name}' in PR head or base branch"
    )


def check_certification_projects(
    source_root: Path,
    base_root: Path | None,
    operator_names: set[str],
) -> str:
    """
    Validate cert_project_id for all affected operators.

    Args:
        source_root (Path): PR head repository root
        base_root (Path | None): Base branch repository root
        operator_names (set[str]): Operator names to check

    Returns:
        str: Certification project ID from the last validated operator

    Raises:
        ValueError: When no operators are affected or cert_project_id is missing
        FileNotFoundError: When ci.yaml cannot be resolved
    """
    if not operator_names:
        raise ValueError("No operator is affected.")

    cert_project_id = ""
    for operator_name in sorted(operator_names):
        ci_path = resolve_operator_ci_yaml_path(source_root, base_root, operator_name)
        config = load_yaml(ci_path)
        project_id = (config or {}).get("cert_project_id")
        if not project_id:
            raise ValueError(
                f"Certification project ID is missing in '{ci_path}' (cert_project_id)"
            )
        cert_project_id = project_id

    return cert_project_id


def main() -> None:
    """
    Main function of the script
    """
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)

    if args.cert_project_required != "true":
        LOGGER.info("Cert project ID is not required.")
        if args.output_file:
            Path(args.output_file).write_text("", encoding="utf-8")
        return

    operator_names = collect_affected_operators(
        args.affected_operators, args.affected_catalog_operators
    )

    try:
        cert_project_id = check_certification_projects(
            args.repo_head_path,
            args.repo_base_path,
            operator_names,
        )
    except (FileNotFoundError, ValueError) as exc:
        LOGGER.error("%s", exc)
        sys.exit(1)
    LOGGER.info("Certification project ID: %s", cert_project_id)
    if args.output_file:
        Path(args.output_file).write_text(cert_project_id, encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    main()
