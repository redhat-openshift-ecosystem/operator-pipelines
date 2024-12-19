# Troubleshooting the Community Operator Pipeline

## Table of Contents

### [Operator Hosted Pipeline](#hosted)
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

### [Operator Released Pipeline](#released)
* [set-github-started-label](#set-github-started-label)
* [set-github-status-pending](#set-github-status-pending)
* [set-env](#set-env)
* [clone-repository-base](#clone-repository-base)
* [clone-repository](#clone-repository)
* [detect-changes](#detect-changes)
* [read-config](#read-config)
* [resolve-pr-type](#resolve-pr-type)
* [content-hash](#content-hash)
* [certification-project-check](#certification-project-check)
* [get-organization](#get-organization)
* [get-pyxis-certification-data](#get-pyxis-certification-data)
* [copy-bundle-image-to-released-registry](#copy-bundle-image-to-released-registry)
* [get-supported-versions](#get-supported-versions)
* [acquire-lease](#acquire-lease)
* [add-bundle-to-index](#add-bundle-to-index)
* [decide-index-paths](#decide-index-paths)
* [get-manifest-digests](#get-manifest-digests)
* [request-signature](#request-signature)
* [upload-signature](#upload-signature)
* [publish-to-index](#publish-to-index)


# <a id="hosted"></a>Operator Hosted Pipeline

## <a id="get-pr-number"></a>get-pr-number
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="acquire-lease"></a>acquire-lease
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="set-github-started-label"></a>set-github-started-label
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="set-github-status-pending"></a>set-github-status-pending
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="set-env"></a>set-env
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="clone-repository-base"></a>clone-repository-base
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="clone-repository"></a>clone-repository
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="detect-changes"></a>detect-changes
### <a id="pr-title"></a>Pull Request Title
When creating a pull request manually the title of your pull request must follow a predefined format. 

| Prefix | Package Name | Version |
|--------|--------------|---------|
| The word `operator` | Operator package name | Version in parenthesis. DO NOT use a 'v' prefix.|

> Note: The version string in your PR Title must match the version directory in your Operator Bundle.  

### Examples
`operator simple-demo-operator (0.0.0)`

`operator hello-world-certified (1.2.3)`

`operator my-operator (3.2.1)`

## <a id="yaml-lint"></a>yaml-lint

**Warnings** at this step should be addressed if possible but won't result in a failure.  
**Errors** at this step will need to be addressed.  Often errors center around <i>unexpected whitespace</i> at the end of lines or <i>missing newlines</i> at the end of your `yaml` files. 

## <a id="check-permissions"></a>check-permissions
Failures at this step are uncommon. If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="set-github-pr-title"></a>set-github-pr-title
Failures at this step are uncommon. If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="read-config"></a>read-config
Failures at this step are uncommon. If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="resolve-pr-type"></a>resolve-pr-type
Failures at this step are uncommon. If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="apply-test-waivers"></a>apply-test-waivers
Failures at this step are uncommon. If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="content-hash"></a>content-hash
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="certification-project-check"></a>certification-project-check
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support. 

## <a id="get-organization"></a>get-organization
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="get-pyxis-certification-data"></a>get-pyxis-certification-data
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="static-tests"></a>static-tests
The summary of failed static tests will be posted to the Pull Request as a comment with detailed reasons. Fix all of 
failed static tests and retrigger the hosted pipeline. To learn more about static tests, please follow this [documentation](https://redhat-openshift-ecosystem.github.io/operator-pipelines/users/static_checks/).

## <a id="static-tests-results"></a>static-tests-results
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="merge-registry-credentials"></a>merge-registry-credentials
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="digest-pinning"></a>digest-pinning
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="verify-pinned-digest"></a>verify-pinned-digest
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="dockerfile-creation"></a>dockerfile-creation
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="build-bundle"></a>build-bundle
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="make-bundle-repo-public"></a>make-bundle-repo-public
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="get-supported-versions"></a>get-supported-versions
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="add-bundle-to-index"></a>add-bundle-to-index
Failures at this step are uncommon and if they do occur they are often transient.  

Please click the `Close pull request` button in GitHub then click the `Reopen pull request` button.
Closing and re-opening your Pull request will restart the Pipeline. If your PR fails at this step twice in a row please contact Red Hat Support

## <a id="make-index-repo-public"></a>make-index-repo-public
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="get-ci-results-attempt"></a>get-ci-results-attempt
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="preflight-trigger"></a>preflight-trigger
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

> Note: There is a known issue if you Operator only supports OpenShift 4.7 or below. In this case we recommend using the CI Pipeline.

## <a id="evaluate-preflight-result"></a>evaluate-preflight-result
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="get-ci-results"></a>get-ci-results
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="link-pull-request-with-open-status"></a>link-pull-request-with-open-status
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="merge-pr"></a>merge-pr
If hosted pipeline fails at this task with the error message: `Pull request Auto merge is not allowed for this repository (enablePullRequestAutoMerge)` then re-trigger the pipeline by running command `/pipeline restart operator-hosted-pipeline`.  

Another Failure at this step may happen if the pull request is a draft, convert the draft to a pull request and then retry. If this problem persists at this step, contact Red Hat Support.

## <a id="link-pull-request-with-merged-status"></a>link-pull-request-with-merged-status
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

# <a id="released"></a>Operator Released Pipeline

## <a id="copy-bundle-image-to-released-registry"></a>copy-bundle-image-to-released-registry
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="decide-index-paths"></a>decide-index-paths
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="get-manifest-digests"></a>get-manifest-digests
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="request-signatur"></a>request-signatur
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="upload-signature"></a>upload-signature
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.

## <a id="publish-to-index"></a>publish-to-index
Failures at this step are uncommon.  If you do experience a failure or error at this step, contact Red Hat Support.
