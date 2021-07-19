# Operator pipelines

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

To trigger a CI pipeline follow steps bellow:
```bash
oc apply -R -f pipelines
oc apply -R -f tasks

tkn pipeline start operator-ci-pipeline \
  --param git_repo_url=https://github.com/Allda/operator-test-repo.git \
  --param git_repo_name=Allda/operator-test-repo \
  --param git_revision=master \
  --param bundle_path=operators/kogito-operator/1.6.0 \
  --workspace name=pipeline,volumeClaimTemplateFile=test/workspace-template.yml \
  --workspace name=ssh-dir,secret=my-ssh-credentials \
  --showlog
```