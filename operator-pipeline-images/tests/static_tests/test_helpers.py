from typing import Any, Iterator

from operatorcert.static_tests.helpers import skip_fbc
from operator_repo import Operator, Bundle
from unittest.mock import call, MagicMock, patch


@patch("operatorcert.static_tests.helpers.LOGGER")
@patch.object(Operator, "probe", return_value=True)
@patch.object(Bundle, "probe", return_value=True)
def test_skip__fbc(
    mock_bundle: MagicMock, mock_operator: MagicMock, mock_logger: MagicMock
) -> None:

    @skip_fbc
    def check_bundle(bundle: Bundle) -> Iterator[str]:
        yield "processed"

    @skip_fbc
    def check_operator(operator: Operator) -> Iterator[str]:
        yield "processed"

    @skip_fbc
    def check_unknown(unknown: None) -> Iterator[str]:
        yield "processed"

    operator = Operator("test-operator")
    operator.config = {"fbc": {"enabled": True}}
    bundle = Bundle("test-bundle", operator)

    assert list(check_bundle(bundle)) == []
    assert list(check_operator(operator)) == []

    mock_logger.assert_has_calls(
        [
            call.info(
                "Skipping %s for FBC enabled operator %s",
                "check_bundle",
                "test-operator",
            ),
            call.info(
                "Skipping %s for FBC enabled operator %s",
                "check_operator",
                "test-operator",
            ),
        ]
    )

    mock_logger.reset_mock()
    operator.config = {"fbc": {"enabled": False}}
    assert list(check_bundle(bundle)) == ["processed"]
    assert list(check_operator(operator)) == ["processed"]
    mock_logger.assert_not_called()

    mock_logger.reset_mock()
    operator.config = {}
    assert list(check_bundle(bundle)) == ["processed"]
    assert list(check_operator(operator)) == ["processed"]
    mock_logger.assert_not_called()

    # if no operator provided wrapped func is executed
    assert list(check_unknown(None)) == ["processed"]
