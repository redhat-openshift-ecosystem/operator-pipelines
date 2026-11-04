"""Tests for stale GitHub webhook cleanup."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from github import GithubException, UnknownObjectException
from github.Hook import Hook

from operatorcert.entrypoints import remove_stale_github_webhooks

NOW = datetime(2026, 11, 2, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep age comparisons deterministic, including the exact cutoff."""
    clock = MagicMock()
    clock.now.return_value = NOW
    monkeypatch.setattr(remove_stale_github_webhooks, "datetime", clock)


@pytest.mark.parametrize("tz", [None, timezone.utc], ids=["naive-utc", "aware-utc"])
def test_remove_stale_webhooks(tz: timezone | None) -> None:
    """Delete and count only hooks strictly older than seven days."""
    cutoff = (NOW - timedelta(days=7)).replace(tzinfo=tz)
    stale = MagicMock(spec=Hook, created_at=cutoff - timedelta(seconds=1))
    older = MagicMock(spec=Hook, created_at=cutoff - timedelta(days=1))
    at_cutoff = MagicMock(spec=Hook, created_at=cutoff)
    recent = MagicMock(spec=Hook, created_at=cutoff + timedelta(seconds=1))

    count = remove_stale_github_webhooks.remove_stale_webhooks(
        [stale, older, at_cutoff, recent]
    )

    assert count == 2
    stale.delete.assert_called_once_with()
    older.delete.assert_called_once_with()
    at_cutoff.delete.assert_not_called()
    recent.delete.assert_not_called()


def test_remove_stale_webhooks_already_removed() -> None:
    """Log a missing hook and continue without counting it as deleted."""
    missing = MagicMock(spec=Hook, id=123, created_at=NOW - timedelta(days=8))
    missing.delete.side_effect = UnknownObjectException(
        404, {"message": "Not Found"}, {}
    )
    stale = MagicMock(spec=Hook, created_at=NOW - timedelta(days=8))

    with patch.object(remove_stale_github_webhooks, "LOGGER") as logger:
        count = remove_stale_github_webhooks.remove_stale_webhooks([missing, stale])

    assert count == 1
    missing.delete.assert_called_once_with()
    stale.delete.assert_called_once_with()
    logger.info.assert_called_once_with(
        "GitHub webhook %s not found; it may already have been removed", 123
    )


@pytest.mark.parametrize("status", [401, 403, 500])
def test_remove_stale_webhooks_propagates_errors(status: int) -> None:
    """Do not suppress authentication, permission, or server failures."""
    stale = MagicMock(spec=Hook, created_at=NOW - timedelta(days=8))
    error = GithubException(status, {"message": "Deletion failed"}, {})
    stale.delete.side_effect = error

    with pytest.raises(GithubException) as raised:
        remove_stale_github_webhooks.remove_stale_webhooks([stale])

    assert raised.value is error


@pytest.mark.parametrize(
    "cli_args, log_level, removed_count",
    [([], "INFO", 0), (["--verbose"], "DEBUG", 2)],
)
@patch("operatorcert.entrypoints.remove_stale_github_webhooks.Github")
@patch("operatorcert.entrypoints.remove_stale_github_webhooks.setup_logger")
@patch("operatorcert.entrypoints.remove_stale_github_webhooks.LOGGER")
def test_main(
    mock_logger: MagicMock,
    mock_setup_logger: MagicMock,
    mock_github: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    cli_args: list[str],
    log_level: str,
    removed_count: int,
) -> None:
    """Read CLI inputs, clean up repository hooks and log the result."""
    monkeypatch.setattr(
        "sys.argv",
        ["remove-stale-github-webhooks", "--repository", "owner/repo"] + cli_args,
    )
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    hooks = [
        MagicMock(spec=Hook, created_at=NOW - timedelta(days=8))
        for _ in range(removed_count)
    ]
    repository = mock_github.return_value.get_repo.return_value
    repository.get_hooks.return_value = hooks

    remove_stale_github_webhooks.main()

    mock_github.assert_called_once_with(login_or_token="test-token")
    mock_github.return_value.get_repo.assert_called_once_with("owner/repo")
    repository.get_hooks.assert_called_once_with()
    for hook in hooks:
        hook.delete.assert_called_once_with()
    mock_setup_logger.assert_called_once_with(level=log_level)
    mock_logger.info.assert_called_once_with(
        "Removed %d stale GitHub webhooks from %s", removed_count, "owner/repo"
    )


def test_cli_requires_repository() -> None:
    """Require an explicit target repository before cleanup can run."""
    with pytest.raises(SystemExit) as error:
        remove_stale_github_webhooks.setup_argparser().parse_args([])
    assert error.value.code == 2
