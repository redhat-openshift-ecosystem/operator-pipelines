# OpenShift namespaces configuration
Operator pipelines are deployed and run in OpenShift Dedicated clusters.
The deployment of all resources including pipelines, tasks, secrets and others
is managed using Ansible playbooks. In order to be able run the ansible
automated way the initial setup of OpenShift namespaces needs to be executed.
This process is also automated and requires access to a cluster with the `cluster-admin`
privileges.

To initially create and configure namespaces for each environment use following script:

```bash
cd ansible
# Store Ansible vault password in ./vault-password
echo $VAULT_PASSWD > ./vault-password

# Login to a cluster using oc
oc login --token=$TOKEN --server=$OCP_SERVER

# Trigger an automation
./init.sh stage
```

This command triggers Ansible that automates creation of OCP namespace for
given environment and store admin service account token into vault.
