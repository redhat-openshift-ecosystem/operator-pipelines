# Troubleshooting the Community Operator Pipeline

This document provides troubleshooting steps for each Tekton task in the Operator Hosted Pipeline and Operator Release Pipeline, including tasks for FBC-enabled operators in the [community-operators-prod](https://github.com/redhat-openshift-ecosystem/community-operators-prod.git) repository.


## Table of Contents

### [Operator Pipeline Tasks Troubleshooting](#tasks)
* [get-pr-number](#get-pr-number)
* [acquire-lease](#acquire-lease)
* [set-github-started-label](#set-github-started-label)
* [set-github-status-pending](#set-github-status-pending)
* [set-env](#set-env)
* [clone-repository-base](#clone-repository-base)
* [clone-repository](#clone-repository)
* [detect-changes](#detect-changes)
* [yaml-lint](#yaml-lint)
* [check-permissions](#check-permissions)
* [set-github-pr-title](#set-github-pr-title)
* [read-config](#read-config)
* [resolve-pr-type](#resolve-pr-type)
* [apply-test-waivers](#apply-test-waivers)
* [content-hash](#content-hash)
* [certification-project-check](#certification-project-check)
* [get-organization](#get-organization)
* [get-pyxis-certification-data](#get-pyxis-certification-data)
* [static-tests](#static-tests)
* [static-tests-results](#static-tests-results)
* [merge-registry-credentials](#merge-registry-credentials)
* [digest-pinning](#digest-pinning)
* [verify-pinned-digest](#verify-pinned-digest)
* [dockerfile-creation](#dockerfile-creation)
* [build-bundle](#build-bundle)
* [make-bundle-repo-public](#make-bundle-repo-public)
* [get-supported-versions](#get-supported-versions)
* [add-bundle-to-index](#add-bundle-to-index)
* [make-index-repo-public](#make-index-repo-public)
* [get-ci-results-attempt](#get-ci-results-attempt)
* [preflight-trigger](#preflight-trigger)
* [evaluate-preflight-result](#evaluate-preflight-result)
* [get-ci-results](#get-ci-results)
* [link-pull-request-with-open-status](#link-pull-request-with-open-status)
* [merge-pr](#merge-pr)
* [link-pull-request-with-merged-status](#link-pull-request-with-merged-status)
* [copy-bundle-image-to-released-registry](#copy-bundle-image-to-released-registry)
* [decide-index-paths](#decide-index-paths)
* [get-manifest-digests](#get-manifest-digests)
* [request-signature](#request-signature)
* [upload-signature](#upload-signature)
* [publish-to-index](#publish-to-index)

### [FBC-Related Operator Pipeline Tasks Troubleshooting](#fbc-tasks)
* [build-fbc-index-images](#build-fbc-index-images)
* [build-fbc-scratch-catalog](#build-fbc-scratch-catalog)


## <a id="tasks"></a>Operator Pipeline Tasks Troubleshooting

### <a id="get-pr-number"></a>get-pr-number
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="acquire-lease"></a>acquire-lease
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="set-github-started-label"></a>set-github-started-label
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="set-github-status-pending"></a>set-github-status-pending
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="set-env"></a>set-env
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="clone-repository-base"></a>clone-repository-base
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="clone-repository"></a>clone-repository
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="detect-changes"></a>detect-changes
The pipeline may fail at this stage due to the following reasons:
1.	<b>Changing Only Non-Operator Files:</b> If the PR attempts to modify files like ci.yaml without making changes to operator files, the pipeline will fail.
1.	<b>Affecting Multiple Operators:</b> If the PR impacts more than one operator, it will result in a failure.
1.	<b>Modifying Existing Bundles:</b> Changes to existing bundles in the PR are not allowed at this stage.
1.	<b>Deleting Existing Bundles:</b> Deleting bundles is only permissible for FBC-enabled operators.

Other Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

#### <a id="pr-title"></a>Pull Request Title
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="yaml-lint"></a>yaml-lint

**Warnings** at this step should be addressed if possible but won't result in a failure.  
**Errors** at this step will need to be addressed.  Often errors center around <i>unexpected whitespace</i> at the end of lines or <i>missing newlines</i> at the end of your `yaml` files. 

### <a id="check-permissions"></a>check-permissions
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="set-github-pr-title"></a>set-github-pr-title
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="read-config"></a>read-config
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="resolve-pr-type"></a>resolve-pr-type
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="apply-test-waivers"></a>apply-test-waivers
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="content-hash"></a>content-hash
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="certification-project-check"></a>certification-project-check
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="get-organization"></a>get-organization
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="get-pyxis-certification-data"></a>get-pyxis-certification-data
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="static-tests"></a>static-tests
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="static-tests-results"></a>static-tests-results
If the static tests fail, a summary will be posted as a comment on the Pull Request, providing detailed reasons for the failure. The summary of test results will look like as shown below:

![Preflight test run logs example](../img/static_tests_example.png)

To proceed:
1.	Review the comment for the detailed reasons behind the failed static tests.
1.	Fix all the reported issues.
1.	Re-trigger the hosted pipeline using the command: `/pipeline restart operator-hosted-pipeline`

For more information about static tests, refer to the [documentation](../users/static_checks.md).

### <a id="merge-registry-credentials"></a>merge-registry-credentials
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="digest-pinning"></a>digest-pinning
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="verify-pinned-digest"></a>verify-pinned-digest
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="dockerfile-creation"></a>dockerfile-creation
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="build-bundle"></a>build-bundle
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="make-bundle-repo-public"></a>make-bundle-repo-public
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="get-supported-versions"></a>get-supported-versions
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="add-bundle-to-index"></a>add-bundle-to-index
Failures at this stage are rare and often due to transient issues. Start by reviewing the pipeline logs linked in the PipelineRun summary within the PR.

As an initial step, re-trigger the pipeline by adding the appropriate command in the PR comment:
1.	`/pipeline restart operator-hosted-pipeline` for the hosted pipeline.
1.	`/pipeline restart operator-release-pipeline` for the release pipeline.

If the PR fails again after two consecutive attempts, feel free to request assistance in the PR comments. Maintainers will assist in identifying and resolving the issue.

### <a id="make-index-repo-public"></a>make-index-repo-public
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="get-ci-results-attempt"></a>get-ci-results-attempt
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="preflight-trigger"></a>preflight-trigger
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="evaluate-preflight-result"></a>evaluate-preflight-result
At this step, the pipeline will primarily fail if the [dynamic tests](../users/dynamic_checks.md) do not pass completely. A link to the test artifacts will be posted as a comment on the PR, as shown below. 

![Preflight test run logs example](../img/preflight_run_logs_example.png)

Please review this link, as it will provide detailed error information.
Failures at this stage are uncommon. To diagnose the issue:
1.	Review the pipeline logs linked in the PipelineRun summary within the PR.
1.	Examine the test artifacts for detailed error information.

If the logs and artifacts do not clarify the issue, feel free to ask for assistance in the PR comments. Maintainers will help identify and resolve the problem.

### <a id="get-ci-results"></a>get-ci-results
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="link-pull-request-with-open-status"></a>link-pull-request-with-open-status
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="merge-pr"></a>merge-pr
If operator hosted pipeline fails at this task with the error message: `Pull request Auto merge is not allowed for this repository (enablePullRequestAutoMerge)` then re-trigger the pipeline by running command `/pipeline restart operator-hosted-pipeline`.  

Another Failure at this step may happen if the pull request is a draft, convert the draft to a pull request and then retry. If this problem persists at this step, contact Red Hat Support.

### <a id="link-pull-request-with-merged-status"></a>link-pull-request-with-merged-status
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="copy-bundle-image-to-released-registry"></a>copy-bundle-image-to-released-registry
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="decide-index-paths"></a>decide-index-paths
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="get-manifest-digests"></a>get-manifest-digests
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="request-signature"></a>request-signature
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="upload-signature"></a>upload-signature
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="publish-to-index"></a>publish-to-index
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

## <a id="fbc-tasks"></a>FBC-Related Operator Pipeline Tasks Troubleshooting

### <a id="build-fbc-index-images"></a>build-fbc-index-images
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

### <a id="build-fbc-scratch-catalog"></a>build-fbc-scratch-catalog
Failures at this stage are rare. To diagnose the issue, review the pipeline logs linked in the PipelineRun summary within the PR. If the logs don’t clarify the problem, feel free to ask for assistance in the PR comments.  Maintainers will assist in identifying and resolving the issue.

