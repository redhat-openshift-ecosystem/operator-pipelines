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
cat << EOF > my-registry-secret.yml
apiVersion: v1
kind: Secret
metadata:
  name: my-registry-secret
data:
  .dockerconfigjson: < BASE64 ENCODED DOCKER CONFIG >
type: kubernetes.io/dockerconfigjson
EOF

oc create -f my-registry-secret.yml
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
  --param git_repo_url=git@github.com:redhat-openshift-ecosystem/operator-pipelines-test-repo.git \
  --param git_repo_name=redhat-openshift-ecosystem/operator-pipelines-test-repo \
  --param git_revision=main \
  --param bundle_path=operators/kogito-operator/1.6.0 \
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
  --param git_pr_branch=main \
  --param git_pr_title="Test commit for sample PR" \
  --param git_pr_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test-repo/pull/1 \
  --param git_repo_url=git@github.com:redhat-openshift-ecosystem/operator-pipelines-test-repo.git \
  --param git_username=test_user \
  --param bundle_path=operators/kogito-operator/1.6.0 \
  --param pyxis_url=https://catalog.redhat.com/api/containers \
  --param preflight_min_version=1.0.0 \
  --param ci_min_version=1.0.0 \
  --workspace name=repository,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=results,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=registry-credentials,secret=my-registry-secret \
  --showlog
```