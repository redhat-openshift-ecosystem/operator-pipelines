from pathlib import Path

import pytest


@pytest.fixture
def operator_pipelines_path(tmp_path: Path) -> Path:
    ansible_cfg = tmp_path / "ansible.cfg"
    ansible_cfg.write_text(
        """
[defaults]
roles_path=./ansible/roles
inventory=./ansible/inventory/local
"""
    )
    roles_dir = tmp_path / "ansible" / "roles"
    inventory_dir = tmp_path / "ansible" / "inventory"
    playbooks_dir = tmp_path / "ansible" / "playbooks"
    roles_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    inventory_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    playbooks_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    inventory = inventory_dir / "local"
    inventory.write_text("localhost ansible_connection=local\n")
    site_playbook = playbooks_dir / "site.yml"
    site_playbook.write_text(
        """
---
- hosts: localhost
  tasks: []
"""
    )
    return tmp_path


@pytest.fixture
def integration_tests_config_file(tmp_path: Path) -> Path:
    sample_config = """
---
operator_repository:
    url: https://github.com/foo/bar
    token: asdfg
contributor_repository:
    url: https://github.com/foo/baz
    token: something
    ssh_key: ~/.ssh/id_rsa_alt
bundle_registry:
    base_ref: quay.io/user1
    username: user1
    password: secret1
test_registry:
    base_ref: quay.io/user2
    username: user2
    password: secret2
iib:
    url: https://example.com/iib
    keytab: /tmp/keytab
"""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(sample_config)
    return cfg_file
