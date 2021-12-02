# CI/CD

This project uses GitHub actions for CI (tests, linters) and CD (deployment).

## Secrets

Both deployment and E2E tests needs GitHub secrets to work properly.
The following secrets should be kept in the repository:

| Secret name | Secret value | Purpose |
| ----------- | ------------ | ------- |
| BOT_TOKEN | PAT (Personal Access Token) of rh-operator-bundle-test-e2e | E2E tests- fake "partner" account, allows access to repository operator-pipelines-test |
| KUBECONFIG | Kubeconfig of the cluster, where E2E tests should run | E2E tests- resources are deployed to the namespace $SHORT_COMMIT_HASH in this cluster |
| VAULT_PASSWORD | Password to the Ansible Vault stored in the repository | E2E tests- password is needed to decrypt the secrets and thus- recreate the resources |
