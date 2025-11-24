from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import MetaData, event, pool
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
import contextlib
import asyncio
import logging
from typing import AsyncIterator, Optional
from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


# Modern SQLAlchemy 2.0+ async engine configuration
def create_optimized_async_engine():
    """Create async engine with modern best practices and greenlet compatibility."""
    
    # Connection arguments for asyncpg
    connect_args = {
        "server_settings": {
            "application_name": f"{settings.app_name}_api",
            "jit": "off",  # Disable JIT for stability
        },
        "command_timeout": 60,
        "statement_cache_size": 0,  # Disable prepared statement cache to avoid greenlet issues
    }
    
    # Engine configuration for SQLAlchemy 2.0+ with greenlet compatibility
    engine_kwargs = {
        "url": settings.database_url,
        "echo": settings.debug,
        "echo_pool": settings.debug,
        "future": True,  # Enable SQLAlchemy 2.0+ mode
        "connect_args": connect_args,
        
        # Connection Pool Configuration (async engines handle pooling internally)
        "pool_size": 10,  # Number of connections to maintain per service
        "max_overflow": 15,  # Additional connections beyond pool_size
        "pool_timeout": 30,  # Timeout for getting connection from pool
        "pool_recycle": 1800,  # Recycle connections every 30 minutes
        "pool_reset_on_return": "commit",  # Clean state on connection return
        "pool_pre_ping": True,  # Test connections before use
        
        # Async/Greenlet Configuration
        "execution_options": {
            "isolation_level": "READ_COMMITTED",
            "autocommit": False,
        },
        
        # Performance and Reliability  
        "query_cache_size": 1200,  # SQL compilation cache
    }
    
    engine = create_async_engine(**engine_kwargs)
    
    # Event listeners for connection management
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set connection-level pragmas."""
        if hasattr(dbapi_connection, 'execute'):
            # PostgreSQL specific optimizations
            pass
    
    @event.listens_for(engine.sync_engine, "checkout")
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        """Handle connection checkout events."""
        logger.debug("Connection checked out from pool")
    
    return engine

# Create the optimized engine
engine = create_optimized_async_engine()

# Session configuration for SQLAlchemy 1.4
from sqlalchemy.orm import sessionmaker as sync_sessionmaker

# For async sessions in SQLAlchemy 1.4, we create them directly from the engine
def create_async_session():
    """Create async session for SQLAlchemy 1.4."""
    return AsyncSession(engine, autoflush=False, autocommit=False, expire_on_commit=False)

# For backward compatibility, create a factory function
def session_factory():
    """Factory function to create async sessions."""
    return create_async_session()


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """
    Modern async database session dependency with greenlet compatibility.
    
    This implementation ensures proper session lifecycle management and
    prevents greenlet spawn errors through careful session handling.
    """
    session = session_factory()
    try:
        # Ensure connection is established in proper async context
        await session.connection()
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()


# Alias for backward compatibility
get_db = get_async_session


@contextlib.asynccontextmanager
async def get_session_context() -> AsyncIterator[AsyncSession]:
    """
    Context manager for async database sessions with modern error handling.
    
    Use this for complex operations that require manual transaction control.
    """
    session = session_factory()
    try:
        # Establish connection in proper async context
        await session.connection()
        yield session
    except Exception as e:
        await session.rollback()
        logger.error(f"Session context error: {e}")
        raise
    finally:
        await session.close()


# Synchronous database setup for Celery tasks
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create sync engine with optimized settings
sync_engine = create_engine(
    settings.database_url.replace('+asyncpg', ''),
    pool_size=5,  # Smaller pool for sync operations
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Synchronous session factory
sync_session_factory = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

def get_sync_session():
    """Get synchronous database session for Celery tasks and sync contexts."""
    return sync_session_factory()

@contextlib.contextmanager
def get_celery_db_session():
    """
    Context manager for synchronous database sessions in Celery tasks.

    This provides automatic transaction management and proper cleanup
    for background job processing.

    Usage:
        with get_celery_db_session() as db:
            # Your database operations
            account = db.query(EmailAccount).filter_by(id=account_id).first()
            # Commit happens automatically on context exit
    """
    session = sync_session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.error("Celery database session error - rolled back transaction")
        raise
    finally:
        session.close()


# Health check function
async def check_database_health() -> bool:
    """Check database connectivity and health."""
    try:
        async with get_session_context() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def create_tables():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)