"""Module for managing approvable exceptions."""

from enum import Enum

EXCEPTION_LABEL_PREFIX = "exception/"


class WorkflowException(Enum):
    """
    This enum maps exceptions to their identifiers.
    """

    # This exceptions allows operators to have a duplicate name
    # across source catalogs, but still must be unique within
    # the same catalog.
    DUPLICATE_NAME = "duplicate_name"
