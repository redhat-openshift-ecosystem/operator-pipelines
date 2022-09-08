# CI/CD

This project uses GitHub Actions and Ansible for CI (tests, linters) and CD (deployment).

## Secrets

Both deployment and integration tests need GitHub secrets to work properly.
The following secrets should be kept in the repository:

| Secret name | Secret value | Purpose |
| ----------- | ------------ | ------- |
| VAULT_PASSWORD | Password to the preprod Ansible Vault stored in the repository | Deployment of preprod and integration test environments
| VAULT_PASSWORD_PROD | Password to the prod Ansible Vault stored in the repository | Deployment of the production environment
| REGISTRY_USERNAME | Username for authentication to the container registry | Building images
| REGISTRY_PASSWORD | Password for authentication to the container registry | Building images
| GITHUB_TOKEN | GitHub authentication token | Creation of GitHub tags and releases

## Run order

- Validation- run always.
- Build and Push Image/ ppc64le Image- run always. That is intended
to help for the developers to test the image in case of changes.
- Integration Tests- runs only on the merge to `main` (or on manual trigger)
- Deployment- run only after integration tests pass on the `main` branch.

## Integration tests

### When do they run?

Integration tests are a stage of the CI/CD that runs only in two cases:
- On merge to main and before deployment
- On desire (manual action- by clicking "run workflow" via GitHub UI)

### Running integration tests

The orchestration of the integration tests is handled by Ansible. A couple dependencies
must be installed to get started:
  - Ansible
  - Python packages: `openshift`, `pygithub`

To execute the integration tests in a custom environment:

```bash
ansible-pull \
  -U "https://github.com/redhat-openshift-ecosystem/operator-pipelines.git" \
  -i "ansible/inventory/operator-pipeline-integration-tests" \
  -e "oc_namespace=$NAMESPACE" \
  --vault-password-file $VAULT_PASSWORD_PATH \
  ansible/playbooks/operator-pipeline-integration-tests.yml
```

Tags can be used to run select portions of the playbook. For example, the test
resources will be cleaned up at the end of every run. Skipping the `clean` tag
will leave the resources behind for debugging.

```bash
ansible-pull \
  --skip-tags clean \
  -U "https://github.com/redhat-openshift-ecosystem/operator-pipelines.git" \
  -i "ansible/inventory/operator-pipeline-integration-tests" \
  -e "oc_namespace=$NAMESPACE" \
  --vault-password-file $VAULT_PASSWORD_PATH \
  ansible/playbooks/operator-pipeline-integration-tests.yml
```
