"""Tests for certification project check entrypoint."""

from pathlib import Path

import pytest

from operatorcert.entrypoints import certification_project_check


def test_collect_affected_operators() -> None:
    result = certification_project_check.collect_affected_operators(
        ["op-a", "op-b"],
        ["v4.15/op-c", "v4.16/op-d"],
    )
    assert result == {"op-a", "op-b", "op-c", "op-d"}


def test_collect_affected_operators_skips_invalid_catalog_paths() -> None:
    result = certification_project_check.collect_affected_operators(
        [],
        ["invalid", "v4.15/op-c"],
    )
    assert result == {"op-c"}


def test_main_ignores_empty_affected_operators_with_catalog_operators(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    operator_dir = tmp_path / "operators" / "catalog-op"
    operator_dir.mkdir(parents=True)
    (operator_dir / "ci.yaml").write_text(
        "cert_project_id: cert-789\n", encoding="utf-8"
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "certification-project-check",
            "--repo-head-path",
            str(tmp_path),
            "--affected-operators",
            "",
            "--affected-catalog-operators",
            "v4.15/catalog-op",
            "--cert-project-required",
            "true",
        ],
    )

    certification_project_check.main()

    assert "Certification project ID: cert-789" in capsys.readouterr().out


def test_resolve_operator_ci_yaml_path_from_head(tmp_path: Path) -> None:
    operator_dir = tmp_path / "operators" / "my-operator"
    operator_dir.mkdir(parents=True)
    ci_file = operator_dir / "ci.yaml"
    ci_file.write_text("cert_project_id: head-id\n", encoding="utf-8")

    result = certification_project_check.resolve_operator_ci_yaml_path(
        tmp_path, None, "my-operator"
    )

    assert result == ci_file


def test_resolve_operator_ci_yaml_path_falls_back_to_base(tmp_path: Path) -> None:
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    base_ci = base_root / "operators" / "my-operator" / "ci.yaml"
    base_ci.parent.mkdir(parents=True)
    base_ci.write_text("cert_project_id: base-id\n", encoding="utf-8")
    head_root.mkdir()

    result = certification_project_check.resolve_operator_ci_yaml_path(
        head_root, base_root, "my-operator"
    )

    assert result == base_ci


def test_resolve_operator_ci_yaml_path_prefers_head_over_base(tmp_path: Path) -> None:
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    base_ci = base_root / "operators" / "my-operator" / "ci.yaml"
    head_ci = head_root / "operators" / "my-operator" / "ci.yaml"
    base_ci.parent.mkdir(parents=True)
    head_ci.parent.mkdir(parents=True)
    base_ci.write_text("cert_project_id: base-id\n", encoding="utf-8")
    head_ci.write_text("cert_project_id: head-id\n", encoding="utf-8")

    result = certification_project_check.resolve_operator_ci_yaml_path(
        head_root, base_root, "my-operator"
    )

    assert result == head_ci


def test_resolve_operator_ci_yaml_path_missing_in_head_and_base(tmp_path: Path) -> None:
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    base_root.mkdir()
    head_root.mkdir()

    with pytest.raises(FileNotFoundError, match="ci.yaml not found"):
        certification_project_check.resolve_operator_ci_yaml_path(
            head_root, base_root, "my-operator"
        )


def test_check_certification_projects_uses_base_for_deleted_operator(
    tmp_path: Path,
) -> None:
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    base_ci = base_root / "operators" / "removed-op" / "ci.yaml"
    base_ci.parent.mkdir(parents=True)
    base_ci.write_text("cert_project_id: cert-123\n", encoding="utf-8")
    head_root.mkdir()

    result = certification_project_check.check_certification_projects(
        head_root,
        base_root,
        {"removed-op"},
    )

    assert result == "cert-123"


def test_check_certification_projects_missing_cert_project_id(tmp_path: Path) -> None:
    operator_dir = tmp_path / "operators" / "my-operator"
    operator_dir.mkdir(parents=True)
    (operator_dir / "ci.yaml").write_text("fbc:\n  enabled: true\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Certification project ID is missing"):
        certification_project_check.check_certification_projects(
            tmp_path,
            None,
            {"my-operator"},
        )


def test_check_certification_projects_no_operators(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No operator is affected"):
        certification_project_check.check_certification_projects(tmp_path, None, set())


def test_main_exits_on_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "certification-project-check",
            "--repo-head-path",
            str(tmp_path),
            "--affected-operators",
            "missing-op",
            "--cert-project-required",
            "true",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        certification_project_check.main()

    assert exc_info.value.code == 1


def test_main_prints_cert_project_id_without_output_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    operator_dir = tmp_path / "operators" / "my-operator"
    operator_dir.mkdir(parents=True)
    (operator_dir / "ci.yaml").write_text(
        "cert_project_id: cert-456\n", encoding="utf-8"
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "certification-project-check",
            "--repo-head-path",
            str(tmp_path),
            "--affected-operators",
            "my-operator",
            "--cert-project-required",
            "true",
        ],
    )

    certification_project_check.main()

    assert "Certification project ID: cert-456" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("cert_project_required", "expected_output"),
    [
        ("false", ""),
        ("true", "cert-123"),
    ],
)
def test_main(
    tmp_path: Path,
    cert_project_required: str,
    expected_output: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    operator_dir = tmp_path / "operators" / "my-operator"
    operator_dir.mkdir(parents=True)
    (operator_dir / "ci.yaml").write_text(
        "cert_project_id: cert-123\n", encoding="utf-8"
    )
    output_file = tmp_path / "cert_project_id.txt"

    monkeypatch.setattr(
        "sys.argv",
        [
            "certification-project-check",
            "--repo-head-path",
            str(tmp_path),
            "--affected-operators",
            "my-operator",
            "--cert-project-required",
            cert_project_required,
            "--output-file",
            str(output_file),
        ],
    )

    certification_project_check.main()

    captured = capsys.readouterr()
    if cert_project_required == "true":
        assert f"Certification project ID: {expected_output}" in captured.out

    assert output_file.read_text(encoding="utf-8") == expected_output
