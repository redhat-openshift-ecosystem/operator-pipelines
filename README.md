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
Since CI pipeline needs to make some changes in git repository (for example digest pinning)
the pipeline requires a write access to provided git repository. Before running a pipeline
user needs to upload ssh secret key to a cluster where the pipeline will run.

To create a required secret run following command:
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
The CI pipeline requires credentials to push and/or pull from all authenticated
registries. This includes:

* Red Hat terms-based registry (registry.redhat.io)
* The registry specified by the `registry` param (including the internal Openshift registry)

The user must create an auth secret containing the docker config with all
credentials included. For example:

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
The CI pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-ci-pipeline \
  --param git_repo_url=git@github.com:redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_revision=main \
  --param bundle_path=operators/kogito-operator/1.6.0-ok \
  --param registry=quay.io \
  --param image_stream=redhat-isv \
  --workspace name=pipeline,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=ssh-dir,secret=my-ssh-credentials \
  --workspace name=registry-credentials,secret=my-registry-secret \
  --showlog
```

## Operator Hosted pipeline
The Hosted Operator Certification Pipeline is used as a validation of the operator
bundles. It’s an additional (to CI pipeline) layer of validation that has to run within
the Red Hat infrastructure. It contains multiple steps from the CI pipeline.

### Prerequisites
See the [Registry Credentials](#registry-credentials) section.

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
