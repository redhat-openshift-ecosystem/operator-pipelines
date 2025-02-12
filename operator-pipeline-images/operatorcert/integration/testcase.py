"""
Framework for the definition of integration test cases as python classes.
"""

import logging
from typing import TypeVar

from colorama import Fore, Style, init as colorama_init

from operatorcert.integration.config import Config

LOGGER = logging.getLogger("operator-cert")


class BaseTestCase:
    """
    The base class for user-defined integration test cases
    """

    def __init__(self, config: Config, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self.run_id = "(unset)"

    def setup(self) -> None:
        """
        This method is the first to be called in the test execution and should
        create the resources required by the test case
        """

    def watch(self) -> None:
        """
        This method is called after `setup()` and should watch the execution
        of the pipeline and either return when the pipeline has finished or
        raise an exception if it reaches an unexpected state
        """

    def validate(self) -> None:
        """
        This method is called after `watch()` terminates and should check
        the state of all the resources involved in the test case and raise
        an exception if the actual state does not match the expected state
        """

    def cleanup(self) -> None:
        """
        This method is called at the very end of the test case, even if a
        previous step raised an exception; it should be used to free up
        any resources created during the execution of the test
        """

    def run(self, run_id: str) -> None:
        """
        Execute the test case; `setup()`, `watch()`, `validate()` and
        `cleanup()` are called in order
        """
        self.run_id = run_id
        try:
            self.setup()
            self.watch()
            self.validate()
        except Exception as e:
            raise e
        finally:
            self.cleanup()


_test_cases = []


_T = TypeVar("_T", bound=type)


def integration_test_case(test_class: _T) -> _T:
    """
    Decorator used to register a class as a test case
    """
    _test_cases.append(test_class)
    return test_class


def run_tests(config: Config, run_id: str) -> int:
    """
    Executes all the test cases that have been registered using the
    `integration_test_case` decorator

    Return:
        number of test cases that failed
    """
    colorama_init()
    failed = 0
    for test_class in _test_cases:
        test_name = test_class.__name__
        print(f"Running {test_name} ", end="")
        try:
            test_instance = test_class(config, LOGGER)
            test_instance.run(run_id)
            print(f"{Fore.GREEN}PASS{Style.RESET_ALL}")
        except Exception as e:  # pylint: disable=broad-except
            print(f"{Fore.RED}FAIL{Style.RESET_ALL}")
            LOGGER.error("Test %s failed:", test_name, exc_info=e)
            failed += 1
    return failed
