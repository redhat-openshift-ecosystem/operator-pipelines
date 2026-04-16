from unittest.mock import MagicMock, call, patch

from operatorcert.operator_repo import Bundle
from operatorcert.operator_repo.checks import (
    Fail,
    Warn,
    get_checks,
    run_check,
    run_suite,
)


def test_check_result() -> None:
    result1 = Warn("foo")
    result2 = Fail("bar")
    result3 = Warn("foo")
    assert result1 != result2
    assert result1 < result2
    assert result1 == result3
    assert "foo" in str(result1)
    assert "bar" in str(result2)
    assert "foo" in repr(result1)
    assert "bar" in repr(result2)
    assert "warning" in str(result1)
    assert "failure" in str(result2)
    assert {result1, result2, result3} == {result1, result2}


@patch("importlib.import_module")
def test_get_checks(mock_import_module: MagicMock) -> None:
    def check_fake(_something):  # type: ignore
        pass

    fake_module = MagicMock()
    fake_module.check_fake = check_fake
    fake_module.non_check_bar = lambda x: None
    mock_import_module.return_value = fake_module
    assert get_checks("suite.name") == {
        "operator": [check_fake],
        "bundle": [check_fake],
        "operator_catalogs": [check_fake],
    }
    mock_import_module.assert_has_calls(
        [call("suite.name.operator"), call("suite.name.bundle")], any_order=True
    )


@patch("importlib.import_module")
def test_get_checks_skip_check(mock_import_module: MagicMock) -> None:
    def check_fake(_something):  # type: ignore
        pass

    fake_module = MagicMock()
    fake_module.check_fake = check_fake
    fake_module.check_ignore = lambda x: None
    mock_import_module.return_value = fake_module
    assert get_checks("suite.name", skip_tests=["check_ignore"]) == {
        "operator": [check_fake],
        "bundle": [check_fake],
        "operator_catalogs": [check_fake],
    }
    mock_import_module.assert_has_calls(
        [call("suite.name.operator"), call("suite.name.bundle")], any_order=True
    )


@patch("importlib.import_module")
def test_get_checks_missing_modules(mock_import_module: MagicMock) -> None:
    def side_effect(module_name: str) -> None:
        raise ModuleNotFoundError(f"No module named '{module_name}'")

    mock_import_module.side_effect = side_effect
    assert get_checks("suite.name") == {
        "operator": [],
        "bundle": [],
        "operator_catalogs": [],
    }
    mock_import_module.assert_has_calls(
        [call("suite.name.operator"), call("suite.name.bundle")], any_order=True
    )


@patch("importlib.import_module")
def test_get_checks_missing_dependency(mock_import_module: MagicMock) -> None:
    """Test that missing dependencies cause a RuntimeError"""

    def side_effect(module_name: str) -> None:
        # Simulate a missing dependency (e.g., jsonschema)
        raise ModuleNotFoundError("No module named 'jsonschema'")

    mock_import_module.side_effect = side_effect
    try:
        get_checks("suite.name")
        assert False, "Expected RuntimeError to be raised"
    except RuntimeError as e:
        assert "Failed to import suite.name.operator due to error" in str(e)
        assert "jsonschema" in str(e)


@patch("importlib.import_module")
def test_get_checks_unexpected_error(mock_import_module: MagicMock) -> None:
    """Test that unexpected errors during module loading cause a RuntimeError"""

    def side_effect(module_name: str) -> None:
        # Simulate an unexpected error (e.g., SyntaxError, AttributeError)
        raise ValueError("Unexpected error during import")

    mock_import_module.side_effect = side_effect
    try:
        get_checks("suite.name")
        assert False, "Expected RuntimeError to be raised"
    except RuntimeError as e:
        assert "Unexpected error loading module suite.name.operator" in str(e)
        assert "Unexpected error during import" in str(e)


def test_run_check(mock_bundle: Bundle) -> None:
    def check_fake(_something):  # type: ignore
        yield Warn("foo")

    assert list(run_check(check_fake, mock_bundle)) == [
        Warn("foo", "check_fake", mock_bundle)
    ]

    def check_with_exception(_something):  # type: ignore
        raise Exception("bar")

    results = list(run_check(check_with_exception, mock_bundle))
    assert results == [
        Fail(
            # Copying the exception message
            results[0].reason,
            "check_with_exception",
            mock_bundle,
        )
    ]
    assert 'Exception("bar")' in results[0].reason


@patch("operatorcert.operator_repo.checks.get_checks")
def test_run_suite(mock_get_checks: MagicMock, mock_bundle: Bundle) -> None:
    def check_fake(_something):  # type: ignore
        yield Warn("foo")

    mock_get_checks.return_value = {"bundle": [check_fake], "operator": []}
    assert list(run_suite([mock_bundle], "fake.suite")) == [
        Warn("foo", "check_fake", mock_bundle)
    ]
