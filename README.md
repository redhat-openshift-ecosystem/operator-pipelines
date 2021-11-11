# Operator pipelines

## Prerequisites

**To run any of the pipelines for the first time, multiple cluster resources has to be created.**

See [first-time-run.md](docs/first-time-run.md)

**To publish the image to OCP registry, cluster with registry should be prepared at first.**

See one-time actions necessary to prepare new cluster: [rhc4tp-cluster.md](docs/rhc4tp-cluster.md)

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
```

### Execution
If using the default internal registry, the CI pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-ci-pipeline \
  --use-param-defaults \
  --param git_repo_url=git@github.com:redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_branch=main \
  --param bundle_path=operators/kogito-operator/1.6.0-ok \
  --param env=prod \
  --workspace name=pipeline,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=kubeconfig,secret=kubeconfig \
  --workspace name=ssh-dir,secret=github-ssh-credentials \
  --workspace name=pyxis-api-key,secret=pyxis-api-secret \
  --showlog
```
If using an external registry, the CI pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-ci-pipeline \
  --use-param-defaults \
  --param git_repo_url=git@github.com:redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_branch=main \
  --param bundle_path=operators/kogito-operator/1.6.0-ok \
  --param env=prod \
  --param registry=quay.io \
  --param image_namespace=redhat-isv \
  --workspace name=pipeline,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=kubeconfig,secret=kubeconfig \
  --workspace name=registry-credentials,secret=registry-dockerconfig-secret \
  --workspace name=pyxis-api-key,secret=pyxis-api-secret \
  --showlog
```

To enable opening the PR and uploading the pipeline logs (visible to logs owner in Red Hat Ecosystem Catalog),
pass the following argument:

```bash
    --param submit=true
```

To open the PR with submission, upstream repository name
must be supplied (eg. test-org/test-repo):

```bash
    --param upstream_repo_name=<repository_name>
```

To enable digest pinning, pass the following arguments:

```bash
  --param pin_digests=true \
  --param git_username=<github_user_name> \
  --param git_email=<github_email> \
  --workspace name=ssh-dir,secret=github-ssh-credentials
```

If any of bundle's related images is stored in private registry user needs to
provide registry tokens for all used private registries. See more details about
how to provide registry token in [first-time-run.md](docs/first-time-run.md).

## Operator Hosted pipeline
The Hosted Operator Certification Pipeline is used as a validation of the operator
bundles. It’s an additional (to CI pipeline) layer of validation that has to run within
the Red Hat infrastructure. It contains multiple steps from the CI pipeline, making the CI pipeline optional.
It is triggered by creating the submission pull request, and successfully completes with merging it.

### Installation
```bash
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift/pipelines/operator-hosted-pipeline.yml
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift/tasks
```

### Execution
The hosted pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-hosted-pipeline \
  --use-param-defaults \
  --param git_pr_branch=test-PR-ok \
  --param git_pr_title="operator kogito-operator (1.6.1-ok)" \
  --param git_pr_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test/pull/31 \
  --param git_fork_url=https://github.com/MarcinGinszt/operator-pipelines-test.git \
  --param git_repo_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_username=foo@redhat.com \
  --param git_commit=0aeff5f71e4fc2d4990474780b56d9312554da5a \
  --param git_base_branch=main \
  --param pr_head_label=MarcinGinszt:test-PR-ok \
  --param env=prod \
  --param preflight_min_version=0.0.0 \
  --param ci_min_version=0.0.0 \
  --workspace name=repository,volumeClaimTemplateFile=templates/workspace-template-small.yml \
  --workspace name=results,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=registry-credentials-all,volumeClaimTemplateFile=templates/workspace-template-small.yml \
  --workspace name=registry-credentials,secret=registry-dockerconfig-secret \
  --workspace name=pyxis-ssl-credentials,secret=operator-pipeline-api-certs \
  --workspace name=prow-kubeconfig,secret=prow-kubeconfig \
  --workspace name=preflight-decryption-key,secret=preflight-decryption-key \
  --workspace name=hydra-credentials,secret=hydra-credentials \
  --workspace name=gpg-key,secret=isv-gpg-key \
  --showlog
```

:warning: Only quay-based registries are supported by the hosted pipeline.
There are some quay specific tasks for configuring the repositories where
the bundle and index images are pushed.


## Operator Release pipeline
The Release pipeline runs after the layers of validation (CI (optionally) and Hosted pipeline).
It is used to certify and publish submitted bundle version.
It is triggered by a merged pull request and successfully completes
once the bundle has been distributed to all relevant Operator catalogs and appears in the Red Hat Ecosystem Catalog.



### Installation

```bash
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift/pipelines/operator-release-pipeline.yml
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift/tasks
```

### Execution
The release pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-release-pipeline \
  --use-param-defaults \
  --param git_repo_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_commit=3ffff387caac0a5b475f44c4a54fb45eebb8dd8e \
  --param git_pr_title="operator kogito-operator (1.6.1-ok)" \
  --param git_pr_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test/pull/31 \
  --param is_latest=true \
  --workspace name=repository,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=results,volumeClaimTemplateFile=templates/workspace-template-small.yml \
  --workspace name=image-data,volumeClaimTemplateFile=templates/workspace-template-small.yml \
  --workspace name=pyxis-ssl-credentials,secret=operator-pipeline-api-certs \
  --workspace name=kerberos-keytab,secret=kerberos-keytab \
  --workspace name=registry-credentials,secret=registry-dockerconfig-secret \
  --workspace name=ocp-registry-kubeconfig,secret=ocp-registry-kubeconfig \
  --showlog
```

# operator-pipelines-images
Container images containing the set of tools for Partner Operator Bundle [certification pipelines](https://github.com/redhat-openshift-ecosystem/operator-pipelines).

## Development

To install the python package in a development environment, run:

```bash
pip install ".[dev]"
```

To test the scripts with the pipelines, see [local-dev.md](docs/local-dev.md).

To run unit tests and code style checkers:

```bash
tox
```

# FOR TESTING: REMOVE BEFORE MERGING
