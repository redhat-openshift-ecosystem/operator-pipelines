# Operator pipelines

## Local setup
To create local cluster for sake of testing the pipelines, see [local-dev.md](docs/local-dev.md)

## Operator CI pipeline

Operator CI pipeline is a pipeline that can be triggered by partner on on-premise
infrastructure. The pipeline does basic check of new operator, build it and install
it in ocp environment. After an operator is installed a pre-flight tests are executed
that validates that operator meets minimum requirements for Red Hat OpenShift Certification.
If tests pass a CI pipeline submits a PR for full operator certification workflow.


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
  --workspace name=ssh-dir,secret=my-ssh-credentials \
  --showlog
```

## Operator Hosted pipeline
The Hosted Operator Certification Pipeline is used as a validation of the operator
bundles. It’s an additional (to CI pipeline) layer of validation that has to run within
the Red Hat infrastructure. It contains multiple steps from the CI pipeline.

To trigger a Hosted pipeline follow steps below: 
```bash
oc apply -R -f pipelines/operator-hosted-pipeline.yml
oc apply -R -f tasks

# Install external tasks:
# yaml-lint
curl https://raw.githubusercontent.com/tektoncd/catalog/main/task/yaml-lint/0.1/yaml-lint.yaml | oc apply -f -
# skopeo-copy
curl https://raw.githubusercontent.com/tektoncd/catalog/main/task/skopeo-copy/0.1/skopeo-copy.yaml | oc apply -f -

tkn pipeline start operator-hosted-pipeline \
  --param git_pr_branch=test \
  --param git_pr_title="Test commit for sample PR" \
  --param git_pr_url=https://github.com/Allda/operator-test-repo/pull/1 \
  --param git_repo_url=https://github.com/Allda/operator-test-repo.git \
  --param git_username=test_user \
  --param bundle_path=operators/kogito-operator/1.6.0 \
  --param pyxis_url=https://catalog.redhat.com/api/containers \
  --param preflight_min_version=1.0.0 \
  --param ci_min_version=1.0.0 \
  --workspace name=repository,volumeClaimTemplateFile=templates/workspace-template.yml \
  --workspace name=results,volumeClaimTemplateFile=templates/workspace-template.yml \
  --showlog
```