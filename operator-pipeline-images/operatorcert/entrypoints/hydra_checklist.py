import argparse
import logging
import sys
from typing import Any

from operatorcert import hydra

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Hydra checklist cli tool.")

    parser.add_argument(
        "--cert-project-id", help="Certification project ID", required=True
    )
    parser.add_argument(
        "--hydra-url",
        default="https://connect.redhat.com/hydra/prm",
        help="URL to the Hydra API",
    )
    parser.add_argument(
        "--ignore-publishing-checklist",
        default="false",
        help="Ignore the results of the publishing checklist",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def check_hydra_checklist_status(
    cert_project_id: str, hydra_url: str, ignore_publishing_checklist: bool
) -> Any:
    # query hydra checklist API
    # Not using urljoin because for some reason it will eat up the prm at the end if
    # url doesn't end with a /
    hydra_checklist_url = f"{hydra_url}/v1/projects/{cert_project_id}/checklist/status"

    LOGGER.info("Examining pre-certification checklist from Hydra...")
    hydra_resp = hydra.get(hydra_checklist_url)
    if hydra_resp["completed"]:
        LOGGER.info(
            f"Pre-certification checklist is completed for cert project with id "
            f"{cert_project_id}."
        )
        return

    LOGGER.debug("Checklist overall status is incomplete. Checking individual items...")

    # if checklist is not complete, go through each item and log which ones are missing
    checklist_items = hydra_resp["checklistItems"]
    completed = True
    for item in checklist_items:
        completed = completed and item["completed"]
        if not item["completed"]:
            LOGGER.error(f"Checklist item not completed: {item['title']}")

    if not completed:
        LOGGER.info(
            f"Pre-certification checklist is not completed for cert project with id "
            f"{cert_project_id}."
        )
        if ignore_publishing_checklist:
            return
        sys.exit(1)


def main() -> None:
    """
    Main function
    """
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    logging.basicConfig(level=log_level)

    check_hydra_checklist_status(
        args.cert_project_id, args.hydra_url, args.ignore_publishing_checklist == "true"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
