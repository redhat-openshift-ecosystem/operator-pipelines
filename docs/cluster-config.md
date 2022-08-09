# Cluster Configuration

All OpenShift clusters should shares a common configuration for our pipelines.
There are cluster-wide resources which require modification, such as the
TektonConfig. But there is also a custom EventListener which reports PipelineRun
events to Google Chat for monitoring purposes. This configuration must be applied
manually for now.

To apply these cluster-wide configurations, run the Ansible playbook.

```bash
ansible-playbook \
    -i inventory/clusters \
    -e "clusters={INSERT ANSIBLE HOST LIST}" \
    -e "ocp_token={INSERT TOKEN}" \
    -e "k8s_validate_certs={yes|no}" \
    --vault-password-file "{INSERT FILE}" \
    playbooks/config-ocp-cluster.yml
```
