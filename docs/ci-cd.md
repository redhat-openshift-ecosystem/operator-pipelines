# CI/CD

This project uses GitHub actions for CI (tests, linters) and CD (deployment).

## Secrets

Both deployment and E2E tests need GitHub secrets to work properly.
The following secrets should be kept in the repository:

| Secret name | Secret value | Purpose |
| ----------- | ------------ | ------- |
| BOT_TOKEN | PAT (Personal Access Token) of rh-operator-bundle-test-e2e | E2E tests- fake "partner" account, allows access to repository operator-pipelines-test |
| KUBECONFIG | Kubeconfig of the cluster, where E2E tests should run | E2E tests- resources are deployed to the namespace $SHORT_COMMIT_HASH in this cluster |
| VAULT_PASSWORD | Password to the Ansible Vault stored in the repository | E2E tests- password is needed to decrypt the secrets and thus- recreate the resources |

## Run order

- Validation- run always.
- Build and Push Image/ ppc64le Image- run always. That is intended
to help for the developers to test the image in case of changes.
- E2E-CI- runs only on the merge to main (or on manual trigger)
- Deployment- run only after successful E2E-CI running on main.

## E2E tests

### When do they run?

E2E tests are stage of the CI/CD that runs only in two cases:
- On merge to main and before deployment
- On desire (manual action- by clicking "run workflow" via GitHub UI)

There are future plans to run them in cronjob as a part of the QA workflow.

### E2E tests stages?

- prepare the environment- script [ansible/init-custom-env.sh](../ansible/init-custom-env.sh):
  - prepare the custom project in OpenShift preprod cluster
  - install all of the pipelines dependencies in this project
- prepare the test data by copying operator from branch `e2e-test-operator`-
with custom version
- run the CI pipeline with `tkn` against the prepared branch. 
On success, it creates the PR on this branch.
- run the Hosted pipeline with `tkn` against PR created by CI pipeline. On success,
this PR is merged. 
- TODO: Release pipeline.
- check if pipelines passed- using `oc`
- remove the project, and thus- clean up all associated resources

To read more about the `init-custom-env`, see [developer-guide.md](developer-guide.md).

### E2E tests dependencies
To run successfully, E2E tests are demanding data from different sources:
1. [GitHub secrets](#Secrets)
2. [Operator-Pipelnes-Test](https://github.com/redhat-openshift-ecosystem/operator-pipelines-test):
3. Since Operator-Pipelines are running against the data in given GitHub repository- well, here it is!  
E2E tests are making copy of the branch `e2e-test-operator`, which contains [test operator](https://github.com/redhat-openshift-ecosystem/operator-pipelines-test/tree/e2e-test-operator/operators/test-e2e-operator).  
For sake of tests, new version of this operator is created by adding suffix with git commit hash to existing version `0.0.7`.  
If this branch will be accidentally removed, it is duplicated in branch `e2e-test-operator-backup`.
4. Data in the Pyxis database: 
There are database entities that should exists prior the pipelines are running, which in normal workflow are created by the 
partner via Connect.
Cert Project should exist in the environemnt, where E2E tests are running, 
with the ID corrensponding to entry in the ci.yaml file
in the test data (see point 2.).  
This Cert Project should:
- be accessible to the test partner account (credentials stored in ansbile vault),
- meet the Hydra checklist requirements
