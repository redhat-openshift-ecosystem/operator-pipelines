"""Static tests helper utilities."""

import logging
from functools import wraps
from typing import Any, Callable, Iterator, Sequence

from operatorcert.operator_repo import Bundle, Operator

LOGGER = logging.getLogger("operator-cert")

_affected_operator_files: tuple[str, ...] = ()


def set_affected_operator_files(files: Sequence[str]) -> None:
    """
    Set the list of repo-relative operator files affected by the pull request.
    Used by check_leaks_in_changed_files; call before run_suite.
    """
    global _affected_operator_files  # pylint: disable=global-statement
    _affected_operator_files = tuple(files)


def get_affected_operator_files() -> tuple[str, ...]:
    """Return repo-relative operator files affected by the pull request."""
    return _affected_operator_files


def skip_fbc(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to skip a static check for FBC enabled operators.

    First argument of the decorated function should be either an Operator or a Bundle,
    otherwise the 'check' will be executed as usual.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Iterator[Any]:
        first_arg = args[0]
        if isinstance(first_arg, Bundle):
            operator = first_arg.operator
        elif isinstance(first_arg, Operator):
            operator = first_arg
        else:
            operator = None

        config = operator.config if operator else {}
        if not config.get("fbc", {}).get("enabled", False):
            yield from func(*args, **kwargs)
        else:
            operator_name = operator.operator_name if operator else "<unknown>"
            LOGGER.info(
                "Skipping %s for FBC enabled operator %s", func.__name__, operator_name
            )
        yield from []

    return wrapper
