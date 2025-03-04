""" Static tests helper utilities. """

import logging
from functools import wraps
from typing import Any, Callable, Iterator

from operatorcert.operator_repo import Bundle, Operator

LOGGER = logging.getLogger("operator-cert")


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
