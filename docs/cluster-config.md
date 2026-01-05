# Cluster Configuration

All OpenShift clusters should share a common configuration for our pipelines.
There are cluster-wide resources which require modification, such as the
TektonConfig. But there is also a custom EventListener which reports PipelineRun
events to Slack and a pipeline that uploads the metrics of other pipelines
for monitoring purposes. This configuration must be applied manually for now.

The configuration is managed by Ansible playbooks and are automatically included
in the CI/CD process in Github Actions.

If you want to apply the configuration to a cluster manually, you can use the
following command :

```bash
# For Stage cluster
make configure-stage-cluster

# For Prod cluster
make configure-prod-cluster
```
