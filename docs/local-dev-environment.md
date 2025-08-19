# Local development environment

This document provides instructiion on how to set up an environment for "local"
development of the Operator Pipelines project.

The word "local" in this context means that developer will use existing stage
operator pipelines cluster and use a custom namespace for development.

## Setup & Deployment

A operator pipelines interact with Github repositories (certified, marketplace and
community). It is highly recomended to `fork` the upstream repository and only work
on your fork.

1. Fork the upstream repository:
   1. [Certified Operators](https://github.com/redhat-openshift-ecosystem/certified-operators-preprod/)
   2. [Community Operators](https://github.com/redhat-openshift-ecosystem/community-operators-pipeline-preprod)
2. Set environment variables referencing your fork:
   1. Create `.env` file in the root of the repository.
   2. Add the following variables to the `.env` file:
      1. `GITHUB_USER` - your GitHub username
3. Sign in to the OpenShift cluster using `oc` CLI:
   ```bash
   oc login --web --server=https://api.pipelines-stage.0ce8.p1.openshiftapps.com:6443
   ```
4. Use a `Makefile` to build and deploy your namespace:
   1. `make deploy-playground`
   2. This will create a new namespace `$(USER)-playground` and deploy the operator pipelines
      to it.
5. Add a Github webhook to your forked repositories:
   1. Go to your forked repository settings.
   2. Add a new webhook with the following settings:
      - **Payload URL**: `https://webhook-dispatcher-$(USER)-playground.operator-pipeline-stage.apps.pipelines-stage.0ce8.p1.openshiftapps.com/api/v1/webhooks/github-pipeline`
      - **Content type**: `application/json`
      - **Secret**: Use the value from `ansible/vaults/common/github-webhook-secret-preprod.txt`.
      - **Which events would you like to trigger this webhook?**: Select "Let me select individual events" and check "Pull requests and Labels".
      - **Active**: Ensure the webhook is active.

## Trigger a pipeline event
Once the environment is set up, you can submit a new pull request to your forked repository.
When opening your PR you need to target the branch `$USER` (the same as your local user).
This will trigger the webhook and start the operator pipelines and process the pull request.

After a moment you should see the pipeline running in the OpenShift console and also see
firts interaction in the PR comments and labels being added to the PR.
