"""A database manager for the webhook dispatcher."""

import logging
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from operatorcert.webhook_dispatcher.config import DatabaseConfig
from operatorcert.webhook_dispatcher.models import Base

LOGGER = logging.getLogger("operator-cert")


class DatabaseManager:
    """
    Database manager for handling connections and sessions.
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine: Engine | None = None
        self._session_factory: Any | None = None

    @property
    def engine(self) -> Engine:
        """
        Get or create the SQLAlchemy engine.

        Returns:
            Engine: A SQLAlchemy engine instance
        """
        if self._engine is None:
            self._engine = create_engine(
                self.config.url,
                echo=self.config.echo,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_pre_ping=True,  # Enable connection health checks
                pool_recycle=3600,  # Recycle connections every hour
            )
        return self._engine

    @property
    def session_factory(self) -> Any:
        """Get or create the session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )
        return self._session_factory

    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            LOGGER.debug("Creating database tables")
            Base.metadata.create_all(bind=self.engine)
            LOGGER.debug("Database tables created successfully")
        except SQLAlchemyError:
            LOGGER.exception("Failed to create database tables")
            raise

    def drop_tables(self) -> None:
        """Drop all database tables."""
        try:
            LOGGER.debug("Dropping database tables")
            Base.metadata.drop_all(bind=self.engine)
            LOGGER.debug("Database tables dropped successfully")
        except SQLAlchemyError:
            LOGGER.exception("Failed to drop database tables")
            raise

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        This ensures that sessions are properly committed or rolled back.

        Yields:
            Session: SQLAlchemy session object
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Database session error")
            session.rollback()
            raise
        finally:
            session.close()

    def get_session_sync(self) -> Any:
        """
        Get a database session (non-context manager version).

        Returns:
            Any: SQLAlchemy session object
        """
        return self.session_factory()

    def health_check(self) -> bool:
        """
        Perform a database health check.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Database health check failed")
            return False


# Global database manager instance
_DB_MANAGER: DatabaseManager | None = None


def init_database(config: DatabaseConfig) -> DatabaseManager:
    """
    Initialize the global database manager.

    Args:
        config: Database configuration

    Returns:
        DatabaseManager: Initialized database manager
    """
    # Database manager should be initialized only once
    global _DB_MANAGER  # pylint: disable=global-statement
    LOGGER.info("Initializing database manager")
    _DB_MANAGER = DatabaseManager(config)
    return _DB_MANAGER


def get_database() -> DatabaseManager:
    """
    Get the global database manager instance.

    Returns:
        DatabaseManager: The global database manager

    Raises:
        RuntimeError: If database manager is not initialized
    """
    if _DB_MANAGER is None:
        raise RuntimeError(
            "Database manager not initialized. Call init_database() first."
        )
    return _DB_MANAGER


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency function to get database session.

    Yields:
        Session: SQLAlchemy session
    """
    db_manager = get_database()
    with db_manager.get_session() as session:
        yield session
