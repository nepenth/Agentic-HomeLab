from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
try:
    from sqlalchemy.ext.asyncio import async_sessionmaker
except ImportError:
    # For older SQLAlchemy versions
    from sqlalchemy.ext.asyncio import async_session as async_sessionmaker
from sqlalchemy import MetaData
import contextlib
from typing import AsyncIterator
from app.config import settings

try:
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        """Base class for all database models."""
        pass
except ImportError:
    # For older SQLAlchemy versions
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
async_session_factory = async_sessionmaker(engine)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Dependency to get async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for backward compatibility
get_db = get_async_session


@contextlib.asynccontextmanager
async def get_session_context() -> AsyncIterator[AsyncSession]:
    """Context manager to get async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)