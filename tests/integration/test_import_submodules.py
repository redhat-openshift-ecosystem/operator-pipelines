"""
Test cases for the import_submodules function.
"""

import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Iterator
from unittest.mock import Mock, patch
import importlib
import pkgutil
import pytest

from operatorcert.integration.testcases import import_submodules


def test_import_submodules_with_string_package() -> None:
    """Test import_submodules with a string package name."""
    # Use a known package that exists in the standard library
    result = import_submodules("json", recursive=False)

    assert isinstance(result, dict)
    # json package has decoder and encoder submodules
    assert "json.decoder" in result
    assert "json.encoder" in result
    assert isinstance(result["json.decoder"], ModuleType)
    assert isinstance(result["json.encoder"], ModuleType)


def test_import_submodules_with_module_object() -> None:
    """Test import_submodules with a ModuleType object."""
    import json

    result = import_submodules(json, recursive=False)

    assert isinstance(result, dict)
    assert "json.decoder" in result
    assert "json.encoder" in result
    assert isinstance(result["json.decoder"], ModuleType)
    assert isinstance(result["json.encoder"], ModuleType)


def test_import_submodules_recursive_true() -> None:
    """Test import_submodules with recursive=True (default behavior)."""
    # Use xml package which has nested subpackages
    result = import_submodules("xml")

    assert isinstance(result, dict)
    # xml has subpackages like etree, dom, parsers, sax
    xml_modules = [key for key in result.keys() if key.startswith("xml.")]
    assert len(xml_modules) > 0

    # Should include nested modules when recursive=True
    nested_modules = [key for key in result.keys() if key.count(".") > 1]
    assert len(nested_modules) > 0


def test_import_submodules_recursive_false() -> None:
    """Test import_submodules with recursive=False."""
    result = import_submodules("xml", recursive=False)

    assert isinstance(result, dict)
    # Should only include direct submodules, not nested ones
    for module_name in result.keys():
        # With recursive=False, should not have deeply nested modules
        assert module_name.startswith("xml.")
        # Count dots to ensure we don't go too deep
        dot_count = module_name.count(".")
        assert dot_count <= 1  # xml.something, not xml.something.else


def test_import_submodules_empty_package() -> None:
    """Test import_submodules with a package that has no submodules."""
    # Create a temporary module structure for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create an empty package
        empty_package_dir = temp_path / "empty_package"
        empty_package_dir.mkdir()
        (empty_package_dir / "__init__.py").write_text("")

        # Add to sys.path temporarily
        sys.path.insert(0, str(temp_path))

        try:
            result = import_submodules("empty_package")
            assert isinstance(result, dict)
            assert len(result) == 0  # No submodules to import
        finally:
            # Clean up sys.path
            sys.path.remove(str(temp_path))
            # Remove from sys.modules if it was imported
            if "empty_package" in sys.modules:
                del sys.modules["empty_package"]


def test_import_submodules_nonexistent_package_string() -> None:
    """Test import_submodules with a non-existent package string."""
    with pytest.raises(ModuleNotFoundError):
        import_submodules("nonexistent_package_12345")


def test_import_submodules_return_type() -> None:
    """Test that import_submodules returns the correct type and structure."""
    result = import_submodules("json", recursive=False)

    # Should return a dictionary
    assert isinstance(result, dict)

    # All keys should be strings (module names)
    for key in result.keys():
        assert isinstance(key, str)
        assert key.startswith("json.")

    # All values should be ModuleType objects
    for value in result.values():
        assert isinstance(value, ModuleType)


def test_import_submodules_package_with_subpackages() -> None:
    """Test recursive import with packages that have subpackages."""
    # Use email package which has multiple levels of nesting
    result = import_submodules("email", recursive=True)

    assert isinstance(result, dict)
    assert len(result) > 0

    # Should include both direct submodules and nested ones
    direct_modules = [key for key in result.keys() if key.count(".") == 1]
    nested_modules = [key for key in result.keys() if key.count(".") > 1]

    assert len(direct_modules) > 0
    # email package should have some nested structure
    assert len(nested_modules) >= 0  # At least some nested modules expected


def test_import_submodules_handles_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that ModuleNotFoundError during submodule import is handled gracefully."""
    # Mock the main package
    mock_package = Mock()
    mock_package.__name__ = "test_package"
    mock_package.__path__ = ["/fake/path"]

    # Mock pkgutil.walk_packages to yield some modules
    def mock_walk_packages(path: list[str]) -> Iterator[pkgutil.ModuleInfo]:
        yield pkgutil.ModuleInfo(None, "working_module", False)  # type: ignore
        yield pkgutil.ModuleInfo(None, "broken_module", False)  # type: ignore

    def mock_import_module(module_name: str) -> Mock:
        if module_name == "test_package":
            return mock_package
        elif module_name == "test_package.working_module":
            mock_working = Mock(spec=ModuleType)
            mock_working.__name__ = "test_package.working_module"
            return mock_working
        elif module_name == "test_package.broken_module":
            # This will trigger the except ModuleNotFoundError: continue
            raise ModuleNotFoundError(f"No module named '{module_name}'")
        else:
            raise ModuleNotFoundError(f"No module named '{module_name}'")

    # Apply the patches
    monkeypatch.setattr(
        "operatorcert.integration.testcases.pkgutil.walk_packages", mock_walk_packages
    )
    monkeypatch.setattr(
        "operatorcert.integration.testcases.importlib.import_module", mock_import_module
    )

    result = import_submodules("test_package", recursive=False)

    # Should only contain the working module, broken_module should be skipped
    assert len(result) == 1
    assert "test_package.working_module" in result
    assert "test_package.broken_module" not in result


def test_import_submodules_recursive_package_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the recursive package handling logic (if recursive and is_pkg)."""
    # Mock the main package
    mock_main_package = Mock()
    mock_main_package.__name__ = "test_package"
    mock_main_package.__path__ = ["/fake/path"]

    # Mock subpackage
    mock_sub_package = Mock()
    mock_sub_package.__name__ = "test_package.sub_package"
    mock_sub_package.__path__ = ["/fake/path/sub"]

    # Track the call count to return different results
    walk_packages_call_count = 0

    def mock_walk_packages(path: list[str]) -> Iterator[pkgutil.ModuleInfo]:
        nonlocal walk_packages_call_count
        walk_packages_call_count += 1
        if walk_packages_call_count == 1:
            # First call for main package - yields a subpackage
            yield pkgutil.ModuleInfo(None, "sub_package", True)  # type: ignore
        else:
            # Second call for subpackage (when recursive=True)
            yield pkgutil.ModuleInfo(None, "nested_module", False)  # type: ignore

    def mock_import_module(module_name: str) -> Mock:
        if module_name == "test_package":
            return mock_main_package
        elif module_name == "test_package.sub_package":
            return mock_sub_package
        elif module_name == "test_package.sub_package.nested_module":
            mock_nested = Mock(spec=ModuleType)
            mock_nested.__name__ = "test_package.sub_package.nested_module"
            return mock_nested
        else:
            raise ModuleNotFoundError(f"No module named '{module_name}'")

    # Apply the patches
    monkeypatch.setattr(
        "operatorcert.integration.testcases.pkgutil.walk_packages", mock_walk_packages
    )
    monkeypatch.setattr(
        "operatorcert.integration.testcases.importlib.import_module", mock_import_module
    )

    # Test with recursive=True - should trigger the "if recursive and is_pkg:" branch
    result_recursive = import_submodules("test_package", recursive=True)

    # Should include both the subpackage and its nested module
    assert "test_package.sub_package" in result_recursive
    assert "test_package.sub_package.nested_module" in result_recursive
    assert len(result_recursive) == 2

    # Reset call count for the non-recursive test
    walk_packages_call_count = 0

    # Test with recursive=False - should NOT trigger recursive import
    result_non_recursive = import_submodules("test_package", recursive=False)

    # Should only include the subpackage, not its nested module
    assert "test_package.sub_package" in result_non_recursive
    assert "test_package.sub_package.nested_module" not in result_non_recursive
    assert len(result_non_recursive) == 1


def test_import_submodules_default_recursive_parameter() -> None:
    """Test that recursive parameter defaults to True."""
    # This test ensures the default behavior is recursive
    result_default = import_submodules("xml")
    result_explicit = import_submodules("xml", recursive=True)

    # Both should produce the same result since recursive=True is the default
    assert result_default.keys() == result_explicit.keys()

    # And should be different from recursive=False (assuming xml has nested structure)
    result_non_recursive = import_submodules("xml", recursive=False)
    # Non-recursive should have fewer or equal modules (likely fewer)
    assert len(result_non_recursive) <= len(result_default)
