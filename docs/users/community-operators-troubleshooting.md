# Troubleshooting the Community Operator Pipeline

This document provides troubleshooting steps for each Tekton task in the Operator Hosted Pipeline and Operator Release Pipeline, including tasks for FBC-enabled operators in the [community-operators-prod](https://github.com/redhat-openshift-ecosystem/community-operators-prod.git) repository.


## Table of Contents

- [Troubleshooting the Community Operator Pipeline](#troubleshooting-the-community-operator-pipeline)
  - [Table of Contents](#table-of-contents)
  - [Operator Pipeline Tasks Troubleshooting](#operator-pipeline-tasks-troubleshooting)
    - [get-pr-number](#get-pr-number)
    - [acquire-lease](#acquire-lease)
    - [set-github-started-label](#set-github-started-label)
    - [set-github-status-pending](#set-github-status-pending)
    - [set-env](#set-env)
    - [clone-repository-base](#clone-repository-base)
    - [clone-repository](#clone-repository)
    - [detect-changes](#detect-changes)
    - [yaml-lint](#yaml-lint)
    - [check-permissions](#check-permissions)
    - [set-github-pr-title](#set-github-pr-title)
    - [read-config](#read-config)
    - [resolve-pr-type](#resolve-pr-type)
    - [apply-test-waivers](#apply-test-waivers)
    - [content-hash](#content-hash)
    - [certification-project-check](#certification-project-check)
    - [get-organization](#get-organization)
    - [get-pyxis-certification-data](#get-pyxis-certification-data)
    - [static-tests](#static-tests)
    - [static-tests-results](#static-tests-results)
    - [merge-registry-credentials](#merge-registry-credentials)
    - [digest-pinning](#digest-pinning)
    - [verify-pinned-digest](#verify-pinned-digest)
    - [dockerfile-creation](#dockerfile-creation)
    - [build-bundle](#build-bundle)
    - [make-bundle-repo-public](#make-bundle-repo-public)
    - [get-supported-versions](#get-supported-versions)
    - [add-bundle-to-index](#add-bundle-to-index)
    - [make-index-repo-public](#make-index-repo-public)
    - [get-ci-results-attempt](#get-ci-results-attempt)
    - [preflight-trigger](#preflight-trigger)
    - [evaluate-preflight-result](#evaluate-preflight-result)
    - [get-ci-results](#get-ci-results)
    - [link-pull-request-with-open-status](#link-pull-request-with-open-status)
    - [merge-pr](#merge-pr)
    - [link-pull-request-with-merged-status](#link-pull-request-with-merged-status)
    - [copy-bundle-image-to-released-registry](#copy-bundle-image-to-released-registry)
    - [decide-index-paths](#decide-index-paths)
    - [get-manifest-digests](#get-manifest-digests)
    - [request-signature](#request-signature)
    - [upload-signature](#upload-signature)
    - [publish-to-index](#publish-to-index)
  - [FBC-Related Operator Pipeline Tasks Troubleshooting](#fbc-related-operator-pipeline-tasks-troubleshooting)
    - [build-fbc-index-images](#build-fbc-index-images)
    - [build-fbc-scratch-catalog](#build-fbc-scratch-catalog)


## Operator Pipeline Tasks Troubleshooting

### get-pr-number
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### acquire-lease
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### set-github-started-label
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### set-github-status-pending
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### set-env
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### clone-repository-base
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### clone-repository
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### detect-changes
The pipeline may fail at this stage due to the following reasons:

1.	<b>Changing Non-Operator Files:</b> If the PR attempts to modify external files outside of targeted operator, the pipeline will fail.
1.	<b>Affecting Multiple Operators:</b> If the PR impacts more than one operator, it will result in a failure.
1.	<b>Modifying Existing Bundles:</b> Changes to existing bundles in the PR are not allowed at this stage.
1.	<b>Deleting Existing Bundles:</b> Deleting bundles is only permissible for FBC-enabled operators.

Other Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### yaml-lint

**Warnings** at this step should be addressed if possible but won't result in a failure.
**Errors** at this step will need to be addressed.  Often errors center around <i>unexpected whitespace</i> at the end of lines or <i>missing newlines</i> at the end of your `yaml` files.

### check-permissions
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### set-github-pr-title
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### read-config
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### resolve-pr-type
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### apply-test-waivers
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### content-hash
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### certification-project-check
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### get-organization
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### get-pyxis-certification-data
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### static-tests
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### static-tests-results
If the static tests fail, a summary will be posted as a comment on the Pull Request, providing detailed reasons for the failure. The summary of test results will look like as shown below:

![Preflight test run logs example](../img/static_tests_example.png)

To proceed:

1.	Review the comment for the detailed reasons behind the failed static tests.
1.	Fix all the reported issues.
1.	Commit the changes with a fix to the PR and it will Re-trigger the hosted pipeline.

For more information about static tests, refer to the [documentation](../users/static_checks.md).

### merge-registry-credentials
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### digest-pinning
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### verify-pinned-digest
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### dockerfile-creation
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### build-bundle
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### make-bundle-repo-public
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### get-supported-versions
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### add-bundle-to-index
Failures at this stage are rare and often due to transient issues. Start by reviewing the pipeline logs linked in the PipelineRun summary within the PR.

As an initial step, re-trigger the pipeline by adding the appropriate command in the PR comment:

1.	`/pipeline restart operator-hosted-pipeline` for the hosted pipeline.
1.	`/pipeline restart operator-release-pipeline` for the release pipeline.

If the PR fails again after two consecutive attempts, feel free to request assistance in the PR comments. Maintainers will assist in identifying and resolving the issue.

### make-index-repo-public
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### get-ci-results-attempt
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### preflight-trigger
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### evaluate-preflight-result
At this step, the pipeline will primarily fail if the [dynamic tests](../users/dynamic_checks.md) do not pass completely. A link to the test artifacts will be posted as a comment on the PR, as shown below.

![Preflight test run logs example](../img/preflight_run_logs_example.png)

Please review this link, as it will provide detailed error information.
Failures at this stage are uncommon. To diagnose the issue:

1.	Review the pipeline logs linked in the PipelineRun summary within the PR.
1.	Examine the test artifacts for detailed error information.

If the logs and artifacts do not clarify the issue, feel free to ask for assistance in the PR comments. Maintainers will help identify and resolve the problem.

### get-ci-results
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### link-pull-request-with-open-status
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### merge-pr
If operator hosted pipeline fails at this task with the error message: `Pull request Auto merge is not allowed for this repository (enablePullRequestAutoMerge)` then re-trigger the pipeline by running command `/pipeline restart operator-hosted-pipeline`.

Another Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### link-pull-request-with-merged-status
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### copy-bundle-image-to-released-registry
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### decide-index-paths
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### get-manifest-digests
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### request-signature
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### upload-signature
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### publish-to-index
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

## FBC-Related Operator Pipeline Tasks Troubleshooting

### build-fbc-index-images
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### build-fbc-scratch-catalog
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.
