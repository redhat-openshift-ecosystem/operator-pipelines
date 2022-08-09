# Index Signature Verification

This repository contains a special Tekton pipeline for checking the signature
status of the production index images. For now, it is only intended to be deployed
manually on a single cluster. The pipeline is regularly scheduled via a CronJob
and runs to completion without sending a direct notification upon success or
failure. Instead, it relies on other resources to handle reporting.

The pipeline should be deployed using Ansible.

```bash
ansible-playbook \
    -i inventory/clusters \
    -e "clusters={INSERT ANSIBLE HOST LIST}" \
    -e "ocp_token={INSERT TOKEN}" \
    -e "k8s_validate_certs={yes|no}" \
    --vault-password-file "{INSERT FILE}" \
    playbooks/deploy-index-signature-verification.yml
```
