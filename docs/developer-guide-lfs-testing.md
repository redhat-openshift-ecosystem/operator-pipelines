# Local Git LFS integration test

This guide records the local integration test used for the Git LFS changes in
`operator-pipelines`. The test verifies this flow:

```text
synthetic bundle image
        -> add-bundle-to-fbc renders a catalog larger than 100 MB
        -> commit-push-and-open-pr uploads the catalog with git lfs push
        -> git-clone downloads it with git lfs pull
        -> Ansible checks the file size and SHA-256
```

The test uses a synthetic bundle whose generated catalog is larger than
100 MB. The temporary test configuration was added only to a local
`operator-pipelines` checkout. No source or configuration changes were made to
the external operator test repository (`operator-pipelines-test`). During a run,
Ansible uses temporary branches in that repository for test input, then removes
those branches during cleanup. Do not manually edit or commit test changes
there.

## Before you start

Requirements:

- A local `operator-pipelines` checkout containing the temporary LFS test
  configuration.
- Git LFS, Podman, Ansible, `oc`, and `tkn`.
- Access to the stage OpenShift cluster.
- Permission to push the pipeline image and a large test image to a registry.
- GitHub access and the Ansible integration-test vault password.

Confirm that `oc` is using the expected cluster and user:

```bash
oc whoami
oc whoami --show-server
oc auth can-i create namespace
git lfs version
podman version
tkn version
```

Use a unique `OPERATOR_VERSION_RELEASE` value for every run. It is used in the
OpenShift namespace, temporary branches, and pull requests, so reusing it can
collide with another run.

## 1. Build the test image

The test image is a synthetic bundle with a large CSV description. OPM uses the
description when it renders the catalog, so the generated catalog is larger
than the 100 MB Git LFS threshold. The image is used for rendering only; it is
not installed on the cluster.

Run the following script from the `operator-pipelines` checkout. It creates the
complete Podman build context; no files need to be added to the external
operator test repository:

<details>
<summary>Build-context script</summary>

```bash
python3 - <<'PY'
import json
from pathlib import Path

output = Path("/tmp/community-lfs-fixture")
output.mkdir(parents=True, exist_ok=False)
(output / "manifests").mkdir()
(output / "metadata").mkdir()

package = "test-e2e-community-lfs"
annotations = {
    "operators.operatorframework.io.bundle.mediatype.v1": "registry+v1",
    "operators.operatorframework.io.bundle.manifests.v1": "manifests/",
    "operators.operatorframework.io.bundle.metadata.v1": "metadata/",
    "operators.operatorframework.io.bundle.package.v1": package,
    "operators.operatorframework.io.bundle.channels.v1": "stable",
}
(output / "metadata/annotations.yaml").write_text(
    json.dumps({"annotations": annotations}), encoding="utf-8"
)
(output / "manifests/csv.yaml").write_text(
    json.dumps({
        "apiVersion": "operators.coreos.com/v1alpha1",
        "kind": "ClusterServiceVersion",
        "metadata": {"name": f"{package}.v0.0.0"},
        "spec": {
            "displayName": "Synthetic LFS catalog fixture",
            "description": "LFS render fixture. " * 5_500_000,
            "version": "0.0.0",
            "install": {"strategy": "deployment", "spec": {"deployments": []}},
        },
    }),
    encoding="utf-8",
)
dockerfile = "FROM scratch\n"
dockerfile += "".join(
    f"LABEL {key}={json.dumps(value)}\n" for key, value in annotations.items()
)
dockerfile += "COPY manifests /manifests/\nCOPY metadata /metadata/\n"
(output / "Dockerfile").write_text(dockerfile, encoding="utf-8")
print(f"Created {output}")
PY
```

</details>

Build and publish the test image using its digest:

```bash
export FIXTURE_IMAGE=quay.io/<namespace>/<repository>:lfs-fixture
podman build -t "$FIXTURE_IMAGE" /tmp/community-lfs-fixture
podman push --digestfile /tmp/community-lfs-fixture.digest "$FIXTURE_IMAGE"
cat /tmp/community-lfs-fixture.digest
```

Use the resulting digest, not the mutable tag, in the test command. The script
creates package `test-e2e-community-lfs` and bundle version `0.0.0`.

## 2. Run the test

Run this from the checkout that contains the temporary test configuration:

```bash
make build-and-test-community-fbc-lfs \
  OPERATOR_VERSION_RELEASE=<unique-release> \
  INTEGRATION_TESTS_FBC_LFS_FIXTURE_IMAGE=quay.io/<namespace>/<repository>@sha256:<digest>
```

This command builds and pushes the pipeline image, then runs the Ansible
playbook with `test_type=community-fbc-lfs`.

If the pipeline image is already available, use the same arguments with
`make integration-test-community-fbc-lfs`:

```bash
make integration-test-community-fbc-lfs \
  OPERATOR_VERSION_RELEASE=<unique-release> \
  INTEGRATION_TESTS_FBC_LFS_FIXTURE_IMAGE=quay.io/<namespace>/<repository>@sha256:<digest> \
  PIPELINE_IMAGE=quay.io/<namespace>/<pipeline-image>@sha256:<digest>
```

Ansible then:

1. Clones the existing operator test repository.
2. Creates temporary base and head branches.
3. Adds the test `ci.yaml`, catalog template, bundle version, and
   `release-config.yaml` to those temporary branches.
4. Opens the bundle pull request.
5. Lets the hosted and release pipelines generate the large catalog.
6. Verifies the generated catalog's LFS pointer, size, and SHA-256 after
   downloading it in a fresh checkout.

You do not need to edit the operator test repository or create
`catalogs/v4.20/test-e2e-community-lfs/catalog.yaml` manually. The
`add-bundle-to-fbc` task must create that catalog; otherwise the LFS push path
is not tested.

Observed result: OPM validation passed, and a Git LFS upload/download round
trip succeeded for a catalog of approximately 118 MB.

### Settings that make this an LFS push test

The temporary Ansible test type used these values:

| Setting | Value | Reason |
| --- | --- | --- |
| `integration_tests_operator_package_name` | `test-e2e-community-lfs` | Matches the test image and bundle PR. |
| `integration_tests_ci_pipeline_enabled` | `false` | Sends the bundle directly to the hosted/release flow. |
| `integration_tests_fbc_catalog` | `false` | The release pipeline must create the catalog. |
| `integration_tests_catalog_versions` | `v4.20` | The catalog path is `catalogs/v4.20/...`. |
| `integration_tests_git_base_branch` | `community` | Uses the community operator test setup. |

The temporary catalog template contains only the bundle image reference:

```yaml
schema: olm.template.basic
entries:
  - schema: olm.package
    name: test-e2e-community-lfs
    defaultChannel: stable
  - schema: olm.channel
    name: stable
    package: test-e2e-community-lfs
    entries:
      - name: test-e2e-community-lfs.v0.0.0
  - schema: olm.bundle
    image: <fixture-image-digest>
```

Do not add a generated catalog to the test input. If the catalog already exists
before `add-bundle-to-fbc` runs, this test no longer proves that the task can
create and upload a large LFS-tracked catalog.

### Important: the test target is local-only

`build-and-test-community-fbc-lfs` was a temporary Make target in the local
test configuration. It was removed from the regular integration-test setup
because large-file runs made parallel tests slow and unstable. The production
branch therefore does not contain this target.

If the target is unavailable, do not modify the operator test repository to
compensate. Use a local `operator-pipelines` checkout that contains the
temporary test configuration, or add a new test configuration to
`operator-pipelines` as a separate change.

## 3. Inspect the results

The test namespace follows this pattern:

```text
<user>-comm-fbc-lfs-test-<unique-release>
```

List the PipelineRuns and inspect their logs:

```bash
NAMESPACE=<user>-comm-fbc-lfs-test-<unique-release>
oc get pipelineruns -n "$NAMESPACE"
tkn pipelinerun logs <pipelinerun-name> -n "$NAMESPACE" --timestamps
```

For the push path, look for:

```text
Tracking oversized catalog with Git LFS
Git LFS files staged for push
Verified LFS pointer
Uploading Git LFS objects
Git LFS objects and Git branch pushed successfully.
```

For the pull path, look for:

```text
Git LFS files detected
Downloading Git LFS files...
Git LFS checkout completed.
```

## 4. Verify the downloaded object

The Ansible test performs this check. To repeat it manually, use the generated
catalog branch:

```bash
set -euo pipefail

# Clone the branch without downloading the large LFS file yet.
export GIT_LFS_SKIP_SMUDGE=1
git clone --single-branch --branch <generated-catalog-branch> \
  <test-repository-url> /tmp/lfs-verification
cd /tmp/lfs-verification

CATALOG=catalogs/v4.20/test-e2e-community-lfs/catalog.yaml
test "$(git check-attr filter -- "$CATALOG")" = "$CATALOG: filter: lfs"
git show "HEAD:$CATALOG" > /tmp/catalog.pointer
git lfs pointer --check --file=/tmp/catalog.pointer

EXPECTED_SIZE=$(sed -n 's/^size //p' /tmp/catalog.pointer)
EXPECTED_SHA=$(sed -n 's/^oid sha256://p' /tmp/catalog.pointer)
test "$EXPECTED_SIZE" -ge 100000000

unset GIT_LFS_SKIP_SMUDGE
git lfs pull --include="$CATALOG" --exclude=""
test "$(wc -c < "$CATALOG")" -eq "$EXPECTED_SIZE"
printf '%s  %s\n' "$EXPECTED_SHA" "$CATALOG" | sha256sum --check
```

The test passes when the pointer is valid, the catalog is at least 100 MB, and
the downloaded file has the size and SHA-256 recorded in the pointer.

## 5. Cleanup

The test setup waits for the generated catalog pull request to be merged and for
the release pipeline triggered by that merge to succeed. Only then does it
delete the generated catalog branch and the temporary test branches.

If a pipeline fails, branches are preserved for troubleshooting. Save the logs
first, then remove the temporary branches manually when investigation is
complete. Deleting a branch does not necessarily reclaim remote Git LFS
storage, so use unique test values for later runs.
