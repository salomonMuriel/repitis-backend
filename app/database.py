"""Database engine and session management."""

import logging
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, create_engine

from app.config import settings

logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.environment == "development",  # Log SQL queries in development
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,  # Number of connections to maintain
    max_overflow=10,  # Additional connections when pool is exhausted
)


def get_session() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.

    Yields:
        Session: SQLModel database session

    Example:
        ```python
        @router.get("/items")
        async def get_items(session: SessionDep):
            items = session.exec(select(Item)).all()
            return items
        ```
    """
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


# Type alias for session dependency
SessionDep = Annotated[Session, Depends(get_session)]
