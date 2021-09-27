# Operator pipelines

## Prerequisites

**To run any of the pipelines for the first time, multiple cluster resources has to be created.**

See [first-time-run.md](docs/first-time-run.md)

## Local setup
To create local cluster for sake of testing the pipelines, see [local-dev.md](docs/local-dev.md)


## Operator CI pipeline

Operator CI pipeline is a pipeline that can be triggered by partner on on-premise
infrastructure. The pipeline does basic check of new operator, build it and install
it in ocp environment. After an operator is installed a pre-flight tests are executed
that validates that operator meets minimum requirements for Red Hat OpenShift Certification.
If tests pass a CI pipeline submits a PR for full operator certification workflow.

### Installation
```bash
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift/pipelines/operator-ci-pipeline.yml
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift/tasks

# Install external dependencies
oc apply -f  https://raw.githubusercontent.com/tektoncd/catalog/main/task/yaml-lint/0.1/yaml-lint.yaml
oc apply -f  https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.4/git-clone.yaml
```

### Execution
If using the default internal registry, the CI pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-ci-pipeline \
  --param git_repo_url=git@github.com:redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_branch=main \
  --param bundle_path=operators/kogito-operator/1.6.0-ok \
  --param env=production \
  --workspace name=pipeline,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=kubeconfig,secret=kubeconfig \
  --workspace name=ssh-dir,secret=github-ssh-credentials \
  --showlog
```
If using an external registry, the CI pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-ci-pipeline \
  --param git_repo_url=git@github.com:redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_branch=main \
  --param bundle_path=operators/kogito-operator/1.6.0-ok \
  --param env=production \
  --param registry=quay.io \
  --param image_namespace=redhat-isv \
  --workspace name=pipeline,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=kubeconfig,secret=kubeconfig \
  --workspace name=registry-credentials,secret=registry-dockerconfig-secret \
  --workspace name=pyxis-api-key,secret=pyxis-api-secret \
  --showlog
```

To enable digest pinning, pass the following arguments:

```bash
  --param pin_digests=true \
  --param git_username=<github_user_name> \
  --param git_email=<github_email> \
  --workspace name=ssh-dir,secret=github-ssh-credentials
```

## Operator Hosted pipeline
The Hosted Operator Certification Pipeline is used as a validation of the operator
bundles. It’s an additional (to CI pipeline) layer of validation that has to run within
the Red Hat infrastructure. It contains multiple steps from the CI pipeline, making the CI pipeline optional.
It is triggered by creating the submission pull request, and successfully completes with merging it.

### Installation
```bash
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift/pipelines/operator-hosted-pipeline.yml
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift/tasks

# Install external dependencies
oc apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/yaml-lint/0.1/yaml-lint.yaml
oc apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.4/git-clone.yaml
```

### Execution
The hosted pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-hosted-pipeline \
  --param git_pr_branch=test-PR-ok \
  --param git_pr_title="operator kogito-operator (1.6.1-ok)" \
  --param git_pr_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test/pull/31 \
  --param git_fork_url=https://github.com/MarcinGinszt/operator-pipelines-test.git \
  --param git_repo_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_username=foo@redhat.com \
  --param git_commit=0aeff5f71e4fc2d4990474780b56d9312554da5a \
  --param pr_head_label=MarcinGinszt:test-PR-ok \
  --param bundle_path=operators/kogito-operator/1.6.1-ok \
  --param env=production \
  --param preflight_min_version=1.0.0 \
  --param ci_min_version=1.0.0 \
  --workspace name=repository,volumeClaimTemplateFile=templates/workspace-template-small.yml \
  --workspace name=results,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=registry-credentials,secret=registry-dockerconfig-secret \
  --workspace name=pyxis-ssl-credentials,secret=operator-pipeline-api-certs \
  --workspace name=kubeconfig,secret=kubeconfig \
  --workspace name=github-bot-token,secret=github-bot-token \
  --workspace name=kubeconfig,secret=kubeconfig \
  --workspace name=hydra-credentials,secret=hydra-credentials \
  --showlog
  # TODO: passing kubeconfig here is just a temporary workaround to make the preflight task pass
```


## Operator Release pipeline
The Release pipeline runs after the layers of validation (CI (optionally) and Hosted pipeline).
It is used to certify and publish submitted bundle version.
It is triggered by a merged pull request and successfully completes
once the bundle has been distributed to all relevant Operator catalogs and appears in the Red Hat Ecosystem Catalog.



### Installation

```bash
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift/pipelines/operator-release-pipeline.yml
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift/tasks

# Install external dependencies
oc apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.4/git-clone.yaml
```

### Execution
The release pipeline can be triggered using the tkn CLI like so:


tkn pipeline start operator-release-pipeline \
  --param git_repo_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param bundle_path=operators/kogito-operator/1.6.0-ok \
  --param git_commit=3ffff387caac0a5b475f44c4a54fb45eebb8dd8e \
  --param is_latest=true \
  --workspace name=repository,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=image-data,volumeClaimTemplateFile=templates/workspace-template-small.yml \
  --workspace name=pyxis-ssl-credentials,secret=operator-pipeline-api-certs \
  --workspace name=github-bot-token,secret=github-bot-token \
  --workspace name=registry-credentials,secret=registry-dockerconfig-secret \
  --workspace name=ocp-kubeconfig,secret=ocp-kubeconfig \
  --showlog
