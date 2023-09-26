"""
Entrypoint module for community-pipelines prow tests
"""
import os
import logging
import openshift as oc

from operatorcert.logger import setup_logger


LOGGER = logging.getLogger("operator-cert")


def test_prow_logging() -> None:
    """
    Temporary testing function that logs oc server version and pull_refs
    """
    server_version = oc.get_server_version()
    pull_refs = os.environ.get("PULL_REFS")

    LOGGER.info("OpenShift server version is: %s", server_version)
    LOGGER.info("Logged pull_refs: %s", pull_refs)


def main() -> None:
    """
    Main function for initializing prow tests
    """
    setup_logger()
    test_prow_logging()


if __name__ == "__main__":  # pragma: no cover
    main()
