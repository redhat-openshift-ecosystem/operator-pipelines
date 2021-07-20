# Operator pipelines

## Operator CI pipeline

Operator CI pipeline is a pipeline that can be triggered by partner on on-premise
infrastructure. The pipeline does basic check of new operator, build it and install
it in ocp environment. After an operator is installed a pre-flight tests are executed
that validates that operator meets minimum requirements for Red Hat OpenShift Certification.
If tests pass a CI pipeline submits a PR for full operator certification workflow.

To trigger a CI pipeline follow steps below:

```bash
oc apply -R -f pipelines/operator-ci-pipeline.yml
oc apply -R -f tasks

# Install external yaml-lint task
curl https://raw.githubusercontent.com/tektoncd/catalog/main/task/yaml-lint/0.1/yaml-lint.yaml | oc apply -f -


tkn pipeline start operator-ci-pipeline \
  --param git_repo_url=https://github.com/Allda/operator-test-repo.git \
  --param git_repo_name=Allda/operator-test-repo \
  --param git_revision=master \
  --param bundle_path=operators/kogito-operator/1.6.0 \
  --workspace name=pipeline,volumeClaimTemplateFile=templates/workspace-template.yml \
  --showlog
```

## Operator Hosted pipeline

To trigger a Hosted pipeline follow steps below: 
```bash
oc apply -R -f pipelines/operator-hosted-pipeline.yml
oc apply -R -f tasks

tkn pipeline start operator-hosted-pipeline \
  --param git_pr_branch=test \
  --param git_pr_title="Test commit for sample PR" \
  --param git_pr_url=https://github.com/Allda/operator-test-repo/pull/1 \
  --param git_repo_url=https://github.com/Allda/operator-test-repo.git \
  --param git_username=test_user \
  --param bundle_path=operators/kogito-operator/1.6.0 \
  --param pyxis_url=https://catalog.redhat.com/api/containers \
  --param preflight_latest_version=1.0.0 \
  --param ci_latest_version=1.0.0 \
  --workspace name=repository,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=results,volumeClaimTemplateFile=templates/workspace-template.yml \
  --showlog
```