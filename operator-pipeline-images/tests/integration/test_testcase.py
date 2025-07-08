from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from operatorcert.integration.config import Config
from operatorcert.integration.testcase import (
    BaseTestCase,
    integration_test_case,
    run_tests,
)


@patch("operatorcert.integration.testcase.BaseTestCase.setup")
@patch("operatorcert.integration.testcase.BaseTestCase.watch")
@patch("operatorcert.integration.testcase.BaseTestCase.validate")
@patch("operatorcert.integration.testcase.BaseTestCase.cleanup")
def test_basetestcase(
    mock_cleanup: MagicMock,
    mock_validate: MagicMock,
    mock_watch: MagicMock,
    mock_setup: MagicMock,
) -> None:
    t = BaseTestCase(MagicMock(), MagicMock())

    # happy path
    t.run("20240315143022")
    mock_setup.assert_called_once()
    mock_watch.assert_called_once()
    mock_validate.assert_called_once()
    mock_cleanup.assert_called_once()

    # test raises exception
    for m in (mock_setup, mock_watch, mock_validate, mock_cleanup):
        m.reset_mock()

    mock_watch.side_effect = Exception()
    with pytest.raises(Exception):
        t.run("20240315143023")
    mock_setup.assert_called_once()
    mock_watch.assert_called_once()
    mock_validate.assert_not_called()
    mock_cleanup.assert_called_once()


class GoodTest(BaseTestCase):
    pass


class BadTest(BaseTestCase):
    def watch(self) -> None:
        raise Exception()


@patch("operatorcert.integration.testcase._test_cases")
def test_integration_test_case(mock_test_cases: MagicMock) -> None:
    assert integration_test_case(GoodTest) == GoodTest
    mock_test_cases.append.assert_called_once_with(GoodTest)


@patch("operatorcert.integration.testcase._test_cases", [GoodTest, BadTest, GoodTest])
@patch("operatorcert.integration.testcase.import_testcases")
def test_run(
    mock_import_testcases: MagicMock, integration_tests_config_file: Path
) -> None:
    cfg = Config.from_yaml(integration_tests_config_file)
    assert run_tests(cfg, "20240315143025") == 1
