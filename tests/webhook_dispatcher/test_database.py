from unittest.mock import MagicMock, patch

import pytest
from operatorcert.webhook_dispatcher.config import DatabaseConfig
from operatorcert.webhook_dispatcher.database import (
    DatabaseManager,
    get_database,
    get_db_session,
    init_database,
)
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture
def database_manager() -> DatabaseManager:
    config = DatabaseConfig(
        db_user="user_with_special_chars!@#",
        db_password="password_with_special_chars!@#",
        db_host="localhost",
        db_port="5432",
        db_name="test",
        echo=False,
        pool_size=5,
        max_overflow=10,
    )
    return DatabaseManager(config)


@patch("operatorcert.webhook_dispatcher.database.create_engine")
def test_database_manager_engine(
    mock_create_engine: MagicMock, database_manager: DatabaseManager
) -> None:

    assert database_manager.engine is not None
    assert mock_create_engine.call_count == 1
    assert (
        mock_create_engine.call_args[0][0]
        == "postgresql://user_with_special_chars%21%40%23:password_with_special_chars%21%40%23@localhost:5432/test"
    )
    assert mock_create_engine.call_args[1]["echo"] is False
    assert mock_create_engine.call_args[1]["pool_size"] == 5
    assert mock_create_engine.call_args[1]["max_overflow"] == 10

    assert database_manager.engine is not None
    assert mock_create_engine.call_count == 1


@patch("operatorcert.webhook_dispatcher.database.create_engine")
@patch("operatorcert.webhook_dispatcher.database.sessionmaker")
def test_database_manager_session_factory(
    mock_sessionmaker: MagicMock,
    mock_create_engine: MagicMock,
    database_manager: DatabaseManager,
) -> None:

    assert database_manager.session_factory is not None
    mock_sessionmaker.assert_called_once_with(
        autocommit=False, autoflush=False, bind=database_manager.engine
    )


@patch("operatorcert.webhook_dispatcher.database.DatabaseManager.engine")
@patch("operatorcert.webhook_dispatcher.database.Base.metadata.create_all")
def test_database_manager_create_tables(
    mock_create_all: MagicMock,
    mock_engine: MagicMock,
    database_manager: DatabaseManager,
) -> None:
    database_manager.create_tables()
    mock_create_all.assert_called_once_with(bind=mock_engine)

    mock_create_all.side_effect = SQLAlchemyError("test")
    with pytest.raises(SQLAlchemyError):
        database_manager.create_tables()


@patch("operatorcert.webhook_dispatcher.database.DatabaseManager.engine")
@patch("operatorcert.webhook_dispatcher.database.Base.metadata.drop_all")
def test_database_manager_drop_tables(
    mock_drop_all: MagicMock, mock_engine: MagicMock, database_manager: DatabaseManager
) -> None:
    database_manager.drop_tables()
    mock_drop_all.assert_called_once_with(bind=mock_engine)

    mock_drop_all.side_effect = SQLAlchemyError("test")
    with pytest.raises(SQLAlchemyError):
        database_manager.drop_tables()


@patch("operatorcert.webhook_dispatcher.database.DatabaseManager.session_factory")
def test_database_manager_get_session(
    mock_session_factory: MagicMock, database_manager: DatabaseManager
) -> None:
    mock_session_factory.return_value = MagicMock()

    with database_manager.get_session() as session:
        assert session is not None

    mock_session_factory.return_value.commit.assert_called_once()
    mock_session_factory.return_value.close.assert_called_once()

    mock_session_factory.return_value.commit.side_effect = SQLAlchemyError("test")
    with pytest.raises(SQLAlchemyError):
        with database_manager.get_session() as session:
            assert session is not None


@patch("operatorcert.webhook_dispatcher.database.DatabaseManager.session_factory")
def test_database_manager_get_session_sync(
    mock_session_factory: MagicMock, database_manager: DatabaseManager
) -> None:

    assert database_manager.get_session_sync() == mock_session_factory.return_value


@patch("operatorcert.webhook_dispatcher.database.DatabaseManager.get_session")
def test_database_manager_health_check(
    mock_get_session: MagicMock, database_manager: DatabaseManager
) -> None:
    mock_session = MagicMock()
    mock_session_context = MagicMock()
    mock_session_context.__enter__.return_value = mock_session
    mock_get_session.return_value = mock_session_context

    resp = database_manager.health_check()
    assert resp is True

    mock_session.execute.side_effect = SQLAlchemyError("test")
    resp = database_manager.health_check()
    assert resp is False


@patch("operatorcert.webhook_dispatcher.database.DatabaseManager")
def test_get_database(mock_database_manager: MagicMock) -> None:
    with pytest.raises(RuntimeError):
        get_database()

    init_database(MagicMock())
    assert get_database() is not None


@patch("operatorcert.webhook_dispatcher.database.get_database")
def test_get_db_session(mock_get_database: MagicMock) -> None:
    mock_db_context = MagicMock()
    mock_db_context.__enter__.return_value = MagicMock()
    mock_get_database.return_value.get_session.return_value = mock_db_context

    resp = next(get_db_session())
    assert resp == mock_db_context.__enter__.return_value
