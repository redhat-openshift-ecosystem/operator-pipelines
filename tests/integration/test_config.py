from pathlib import Path

from operatorcert.integration.config import Config


def test_Config(integration_tests_config_file: Path) -> None:
    cfg = Config.from_yaml(integration_tests_config_file)
    assert cfg.operator_repository.url == "https://github.com/foo/bar"
    assert cfg.operator_repository.token == "asdfg"
    assert cfg.contributor_repository.url == "https://github.com/foo/baz"
    assert cfg.contributor_repository.token == "something"
    assert cfg.contributor_repository.ssh_key == Path("~/.ssh/id_rsa_alt")
    assert cfg.bundle_registry.base_ref == "quay.io/user1"
    assert cfg.bundle_registry.username == "user1"
    assert cfg.bundle_registry.password == "secret1"
    assert cfg.test_registry.base_ref == "quay.io/user2"
    assert cfg.test_registry.username == "user2"
    assert cfg.test_registry.password == "secret2"
    assert cfg.iib.url == "https://example.com/iib"
    assert cfg.iib.keytab == Path("/tmp/keytab")
