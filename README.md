# Red Hat ISV Operator Certification Pipelines

Red Hat OpenShift pipelines for certifying ISV Operator Bundles.

## Getting Started

Refer to the [developer guide](docs/developer-guide.md).

> **Note**: This documentation is intended for pipeline **developers/maintainers** only.
>
> Partners/users should refer to
[this](https://github.com/redhat-openshift-ecosystem/certification-releases/blob/main/4.9/ga/operator-cert-workflow.md)
documentation instead.

## Usage

### Operator CI Pipeline

The Operator CI pipeline is a Tekton pipeline that can be triggered by a partner using on-premise
infrastructure. The pipeline validates an Operator Bundle, builds it and installs it to an OpenShift
environment. After installation, pre-flight tests are executed which validate that the Operator meets
minimum requirements for Red Hat OpenShift Certification. If all preceding tasks pass, the CI pipeline
optionally uploads results and submits a pull request to trigger the next stages of the operator
certification workflow.

> **Note:** Execution of the CI pipeline is NOT required in the overall certification workflow.

If using the default internal registry, the CI pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-ci-pipeline \
  --use-param-defaults \
  --param git_repo_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test.git \
  --param git_branch=main \
  --param bundle_path=operators/kogito-operator/1.6.0-ok \
  --param env=prod \
  --workspace name=pipeline,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=kubeconfig,secret=kubeconfig \
  --workspace name=pyxis-api-key,secret=pyxis-api-secret \
  --showlog
```
If using an external registry, the CI pipeline can be triggered using the tkn CLI like so:

```bash
tkn pipeline start operator-ci-pipeline \
  --use-param-defaults \
  --param git_repo_url=https://github.com/redhat-openshift-ecosystem/operator-pipelines-test.git \
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

To enable opening the PR and uploading the pipeline logs (visible to the certification project
owner in Red Hat Connect), pass the following argument:

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
  --param git_repo_url=<github_repo_ssh_url> \
  --param git_username=<github_user_name> \
  --param git_email=<github_email> \
  --workspace name=ssh-dir,secret=github-ssh-credentials
```

> **Note:** The `git_repo_url` param needs an SSH URL to commit the pinned digests.

If any of bundle's related images are stored in a private registry the user needs to provide tokens
to pull from those registries. See more details about how to provide registry tokens in the
[pipeline environment setup documentation](docs/pipeline-env-setup.md#registry-credentials).

### Operator Hosted Pipeline

The hosted pipeline is used to certify the Operator bundles.
It’s an additional (to CI pipeline) layer of validation that has to run within
the Red Hat infrastructure. It is intended to be triggered upon the creation of a
bundle pull request and successfully completes with merging it (configurable).

> **Note:** Execution of the hosted pipeline is ALWAYS required in the overall certification workflow.
Prior execution of the CI pipeline may influence its behavior if results were submitted. Preflight
testing may be skipped in such a case.

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

To ignore the results of the publishing checklist, pass the following argument:

```bash
  --param ignore_publishing_checklist=true
```

:warning: Only quay-based registries are supported by the hosted pipeline.
There are some quay specific tasks for configuring the repositories where
the bundle and index images are pushed.

### Operator Release Pipeline

The release pipeline is responsible for releasing a bundle image which has passed certification.
It's intended to be triggered by the merge of a bundle pull request by the hosted pipeline.
It successfully completes once the bundle has been distributed to all relevant Operator catalogs
and appears in the Red Hat Ecosystem Catalog.

> **Note:** Execution of the release pipeline is ALWAYS required in the overall certification workflow.

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

### Using a Custom Pipeline Image

All the pipelines share a common pipeline image for many of the steps.
This image can be overridden by passing the following to any `tkn pipeline start` command.

```bash
--param pipeline_image=<image-pull-spec>
```
