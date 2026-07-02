---
name: integration-tests
description: Use when setting up or running integration tests for operator-pipelines. Agents should NOT run these — guide the user through manual setup and execution instead.
---

# Integration Tests

## Overview

Integration tests create a PR in repository https://github.com/redhat-openshift-ecosystem/operator-pipelines-test. This PR creation triggers the hosted pipeline that tests compatibility of an added operator version in various ways. After success, PR is merged automatically and a release pipeline is triggered that adds the operator to an index image. The tests take up to tens of minutes and produce extensive Ansible logs. **Agents should not run them** — instead, help the user prepare and point them to the right resources.

### Prerequisites

1. Be logged in to an OpenShift stage cluster:
  ```shell
    oc login --server=https://api.pipelines-stage.0ce8.p1.openshiftapps.com:6443 --token=<token>
  ```
2. Have stage Ansible vault password available in `ansible/vault-password`.
3. Built image is pushed to $PIPELINE_IMAGE_REPO that defaults to `quay.io/redhat-isv/operator-pipelines-test-image`. Either get access to this repo or set up your own repository to store test images.

### Deployment

```bash
# build and deploy the project to a playground namespace
make build-and-deploy-playground
```

### Running Tests

Before running each test:
```bash
# export new release version of a test operator based on previous successfully
# released versions (may look at operator-pipelines-test closed PRs)
export OPERATOR_VERSION_RELEASE="402-1"
```

Then, run any of the available test flows. Passing all of them is required by the CI:
```bash
make build-and-test-isv               # ISV operator flow
make build-and-test-community         # Community operator flow
make build-and-test-isv-fbc-bundle    # ISV FBC bundle flow
make build-and-test-isv-fbc-catalog   # ISV FBC catalog flow
```

More information about the specific env variables and commands used to run these tests is available in the project's `Makefile`.

### Debugging
Recommended tools for basic interaction with running pipelines are `tkn`, `oc` CLI, and OpenShift Console UI.

## Optional setup
In case the developer wants to create and test a custom situation, refer to `docs/local-dev-environment.md`
which provides steps to fork the operator repositories, create webhooks and create custom PRs that trigger
pipelines in the playground namespace.
