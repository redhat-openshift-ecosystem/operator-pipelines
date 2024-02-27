# Cluster Configuration

All OpenShift clusters should share a common configuration for our pipelines.
There are cluster-wide resources which require modification, such as the
TektonConfig. But there is also a custom EventListener which reports PipelineRun
events to Slack and a pipeline that uploads the metrics of other pipelines
for monitoring purposes. This configuration must be applied manually for now.

To apply these cluster-wide configurations, run the Ansible playbook. To only apply
the cluster-wide resources, the following command will suffice.

```bash
ansible-playbook \
    -i inventory/clusters \
    -e "clusters={INSERT ANSIBLE HOST LIST}" \
    -e "ocp_token={INSERT TOKEN}" \
    -e "k8s_validate_certs={yes|no}" \
    --vault-password-file "{INSERT FILE}" \
    playbooks/config-ocp-cluster.yml
```

If you want to deploy the metrics pipeline, add `--tags metrics` to the above command.
To deploy the Chat Webhook, add `--tags chat`. If you wish to deploy both, add
`--tags metrics,chat`.