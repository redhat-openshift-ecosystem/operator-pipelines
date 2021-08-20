# Operator pipelines

## Local setup
To create local cluster for sake of testing the pipelines, see [local-dev.md](docs/local-dev.md)

## Operator CI pipeline

Operator CI pipeline is a pipeline that can be triggered by partner on on-premise
infrastructure. The pipeline does basic check of new operator, build it and install
it in ocp environment. After an operator is installed a pre-flight tests are executed
that validates that operator meets minimum requirements for Red Hat OpenShift Certification.
If tests pass a CI pipeline submits a PR for full operator certification workflow.

### Prerequisites

#### Git SSH Secret
The CI pipeline requires git SSH credentials with write access to the repository if automatic
digest pinning is enabled using the `pin_digests` param. This is disabled by default. Before
executing the pipeline the user must create a secret in the same namespace as the pipeline.

To create the secret run the following commands (substituting your key):
```bash
cat << EOF > ssh-secret.yml
kind: Secret
apiVersion: v1
metadata:
  name: my-ssh-credentials
data:
  id_rsa: |
    < PRIVATE SSH KEY >
EOF

oc create -f ssh-secret.yml
```

#### Registry Credentials
The CI pipeline can optionally be configured to push images to a remote private
registry. The user must create an auth secret containing the docker config. This
secret can then be passed as a workspace named `registry-credentials` when invoking
the pipeline.

```bash
cat << EOF > registry-secret.yml
apiVersion: v1
kind: Secret
metadata:
  name: my-registry-secret
data:
  .dockerconfigjson: < BASE64 ENCODED DOCKER CONFIG >
type: kubernetes.io/dockerconfigjson
EOF

oc create -f registry-secret.yml
```

#### Red Hat Catalog Imagestreams

The pipelines must pull the parent index images through the internal OpenShift
registry to take advantage of the built-in credentials for Red Hat's terms-based
registry (registry.redhat.io). This saves the user from needing to provide such
credentials. The index generation task will always pull published index images
through imagestreams of the same name in the current namespace. As a result,
there is a one time configuration for each desired distribution catalog.

```bash
# Must be run once before certifying against the certified catalog.
oc import-image certified-operator-index \
  --from=registry.redhat.io/redhat/certified-operator-index \
  --reference-policy local \
  --scheduled \
  --confirm \
  --all

# Must be run once before certifying against the Red Hat Martketplace catalog.
oc import-image redhat-marketplace-index \
  --from=registry.redhat.io/redhat/redhat-marketplace-index \
  --reference-policy local \
  --scheduled \
  --confirm \
  --all
```

#### Container API access
CI pipelines automatically upload a test results, logs and artifacts using Red Hat
container API. This requires a partner's API key and the key needs to be created
as a secret in openshift cluster before running a Tekton pipeline.

```bash
oc create secret generic pyxis-api-secret --from-literal PYXIS_API_KEY=< API KEY >
```
### Installation
```bash
oc apply -R -f pipelines/operator-ci-pipeline.yml
oc apply -R -f tasks

# Install external dependencies
curl https://raw.githubusercontent.com/tektoncd/catalog/main/task/yaml-lint/0.1/yaml-lint.yaml | oc apply -f -
curl https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.4/git-clone.yaml | oc apply -f -
```

### Execution
If using the default internal registry, the CI pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-ci-pipeline \
  --param git_repo_url=git@github.com:redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_revision=main \
  --param bundle_path=operators/kogito-operator/1.6.0-ok \
  --workspace name=pipeline,volumeClaimTemplateFile=templates/workspace-template.yml \
  --showlog
```
If using an external registry, the CI pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-ci-pipeline \
  --param git_repo_url=git@github.com:redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_revision=main \
  --param bundle_path=operators/kogito-operator/1.6.0-ok \
  --param registry=quay.io \
  --param image_namespace=redhat-isv \
  --workspace name=pipeline,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=registry-credentials,secret=my-registry-secret \
  --showlog
```

To enable digest pinning, pass the following arguments:

```bash
  --param pin_digests=true \
  --workspace name=ssh-dir,secret=my-ssh-credentials
```

## Operator Hosted pipeline
The Hosted Operator Certification Pipeline is used as a validation of the operator
bundles. It’s an additional (to CI pipeline) layer of validation that has to run within
the Red Hat infrastructure. It contains multiple steps from the CI pipeline.

### Prerequisites
See the [Red Hat Catalog Imagestreams](#red-hat-catalog-imagestreams) section.

### Installation
```bash
oc apply -R -f pipelines/operator-hosted-pipeline.yml
oc apply -R -f tasks

# Install external dependencies
curl https://raw.githubusercontent.com/tektoncd/catalog/main/task/yaml-lint/0.1/yaml-lint.yaml | oc apply -f -
curl https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.4/git-clone.yaml | oc apply -f -
```

### Execution
The hosted pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-hosted-pipeline \
  --param git_pr_branch=test-PR-ok \
  --param git_pr_title="operator kogito-operator (1.6.1-ok)" \
  --param git_pr_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test/pull/2 \
  --param git_fork_url=git@github.com:MarcinGinszt/operator-pipelines-test.git \
  --param git_repo_url=git@github.com:redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_username=test_user \
  --param pr_head_label=MarcinGinszt:test-PR-ok \
  --param bundle_path=operators/kogito-operator/1.6.1-ok \
  --param pyxis_url=https://catalog.redhat.com/api/containers/ \
  --param preflight_min_version=1.0.0 \
  --param ci_min_version=1.0.0 \
  --workspace name=repository,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=results,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=ssh-dir,secret=my-ssh-credentials \
  --workspace name=registry-credentials,secret=my-registry-secret \
  --showlog
```
