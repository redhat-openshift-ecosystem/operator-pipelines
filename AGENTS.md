# operator-pipelines

For a concise summary of the project's purpose, read [pipelines overview](docs/users/pipelines_overview.md).

**Toolchain:** Python, Poetry, tox, Ansible, Tekton (OpenShift Pipelines)

## Architecture

- **Tekton pipelines** (`ansible/roles/operator-pipeline/templates/openshift/pipelines/`) define the end-to-end flows. The main pipelines are:
  - `operator-ci-pipeline.yml` — ISV CI pipeline for partners to test operators on their own infrastructure without submitting to Red Hat.
  - `operator-hosted-pipeline.yml` — Hosted pipeline that accepts operator submissions, runs linting, static checks and dynamic tests (preflight checks), and communicates with Red Hat internal systems to control certification flow. Used for both ISV and community operators.
  - `operator-release-pipeline.yml` — Release pipeline that distributes operators to index images (community-operator-index, certified-operator-index, redhat-marketplace-index).
- **Tekton tasks** (`ansible/roles/operator-pipeline/templates/openshift/tasks/`) are the individual pipeline steps. Tasks typically invoke a Python entrypoint as its container command. See `apply-test-waivers.yml` for a minimal example.
- **Python core logic** (`operatorcert/` covered by unit tests in structurally matching `tests/` folder) — Entrypoints in `operatorcert/entrypoints` registered in `pyproject.toml` as `[project.scripts]` are directly used by Tekton tasks. The `operatorcert` also includes Pyxis, IIB, GitHub, OPM clients and bundle/catalog models used by entrypoints.
- **Documentation** (`docs/`, user-facing `docs/user/`)

## Conventions for making changes to the pipelines

- Avoid including credentials within Task scripts.
  - Avoid the use of `set -x` in shell scripts which _could_ expose credentials
    to the console.
- Don't use workspaces for passing secrets. Use `secretKeyRef` and `volumeMount`
  with secret and key names instead.
  - Reason: It adds unnecessary complexity to `tkn` commands.
- Use images from trusted registries/namespaces.
  - registry.redhat.io
  - registry.access.redhat.com
  - quay.io/redhat-isv
  - quay.io/opdev
- Use image pull specs with digests instead of tags wherever possible.
- Tasks must implement their own skipping behavior, if needed.
  - Reason: If a task is not executed, any dependent tasks will not be
    executed either.
- Don't use ClusterTasks or upstream tasks. All tasks are defined in this repo.
- Document all params, especially pipeline params.
- Output human readable logs.
- Use reasonable defaults for params wherever possible.

## PR Conventions

- Run `tox` (all environments) before submitting. For all the details about the tox environments including unit testing, linting, type checking, formatting, etc. use `skills/running-tests-and-quality-gates`. This includes single-file verification commands, like `poetry run black --check path/to/file.py`, `poetry run mypy --strict --ignore-missing-imports path/to/file.py`, etc.
- Integration tests should NOT be run by an agent as they can take a lot of time to finish and generate extensive logs. Upon asking, agent should inform the developer about the integration tests setup and how to run them manually using `skills/integration-tests/`.
- Test coverage of code should remain at 100%.
- All of the quality gates above are enforced in CI.
