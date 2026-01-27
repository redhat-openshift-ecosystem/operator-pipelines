from typing import Any
from unittest.mock import MagicMock, patch

from operatorcert.webhook_dispatcher.main import main


@patch("operatorcert.webhook_dispatcher.main.threading.Thread")
@patch("operatorcert.webhook_dispatcher.main.EventDispatcher")
@patch("operatorcert.webhook_dispatcher.main.load_config")
@patch("operatorcert.webhook_dispatcher.main.init_database")
@patch("operatorcert.webhook_dispatcher.main.setup_logger")
@patch("operatorcert.webhook_dispatcher.main.app")
@patch("operatorcert.webhook_dispatcher.main.asyncio.run")
@patch("operatorcert.webhook_dispatcher.main.argparse.ArgumentParser")
def test_main(
    mock_argparse: MagicMock,
    mock_asyncio_run: MagicMock,
    mock_app: MagicMock,
    mock_setup_logger: MagicMock,
    mock_init_database: MagicMock,
    mock_load_config: MagicMock,
    mock_dispatcher: MagicMock,
    mock_thread: MagicMock,
    monkeypatch: Any,
) -> None:

    monkeypatch.setenv("WEBHOOK_DISPATCHER_CONFIG", "config/dispatcher_config.yaml")
    monkeypatch.setenv("DISPATCHER_PORT", "5000")

    main()

    mock_app.run.assert_called_once_with(port=5000, host="0.0.0.0")
    mock_load_config.assert_called_once_with("config/dispatcher_config.yaml")
    mock_dispatcher.assert_called_once_with(mock_load_config.return_value.dispatcher)
    mock_thread.return_value.start.assert_called_once()
    mock_init_database.return_value.create_tables.assert_called_once()
