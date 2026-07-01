---
name: running-tests-and-quality-gates
description: Use when running or interacting with unit tests, code formatters, linters, type checks, pip audit or other quality gates.
---

# Running Tests and Quality Gates

## Quick reference

| Check | Command | Single-file alternative |
|---|---|---|
| Unit tests (all) | `tox -e test` | — |
| Unit tests (single file) | — | `tox -e test -- tests/path/to/test_file.py --no-cov` |
| Unit tests (single test) | — | `tox -e test -- -k test_name --no-cov` |
| Unit tests (by path) | — | `tox -e test -- tests/path/to/test_file.py::test_name --no-cov` |
| Format check | `tox -e black` | `poetry run black --check path/to/file.py` |
| Auto-format | `tox -e black-format` | `poetry run black path/to/file.py` |
| Type check (strict) | `tox -e mypy` | `poetry run mypy --strict --ignore-missing-imports path/to/file.py` |
| Static analysis | `tox -e pylint` | — |
| Security scan | `tox -e bandit` | — |
| YAML lint | `tox -e yamllint` | — |
| Ansible lint | `tox -e ansible-lint` | — |
| Dockerfile lint | `tox -e hadolint` | — |
| Dependency audit | `tox -e pip-audit` | — |
| All checks | `tox` | — |

Use `--no-cov` when running single test files or functions — the 100% coverage gate measures the whole package and will fail on partial runs.

Single-file format/type checks use `poetry run` directly — tox envs other than `test` do not pass `{posargs}` to the underlying tool.

## Fast feedback loop

For tight iteration, run scoped checks after each change:

```bash
tox -e test -- tests/path/to/test_file.py --no-cov  # single test file
poetry run black --check path/to/file.py              # format check
poetry run mypy --strict --ignore-missing-imports path/to/file.py  # type check
```

Run the full suite (`tox`) before opening a PR.

## Test layout

Tests mirror the source tree under `tests/`:

```
tests/entrypoints/       # mirrors operatorcert/entrypoints/
tests/static_tests/      # mirrors operatorcert/static_tests/
tests/operator_repo/     # mirrors operatorcert/operator_repo/
tests/catalog/           # mirrors operatorcert/catalog/
...
```

Place new test files in the matching subdirectory. Name them `test_<module_name>.py`.

## Constraints

- **100% unit test coverage enforced** (`--cov-fail-under 100`) — new code needs tests
- **mypy runs in strict mode** — all functions need type annotations, `Any` usage must be explicit
