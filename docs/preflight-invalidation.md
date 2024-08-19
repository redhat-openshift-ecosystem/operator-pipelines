# Preflight invalidation CronJob

The repository contains a CronJob that updates enabled preflight versions
weekly. https://issues.redhat.com/browse/ISV-4964

After changes, the CronJob can be deployed using Ansible.

```bash
ansible-playbook \
    -i ansible/inventory/clusters \
    -e "clusters=prod-cluster" \
    -e "ocp_token=[TOKEN]" \
    -e "env=prod" \
    --vault-password-file [PWD_FILE] \
    playbooks/preflight-invalidation.yml
```
