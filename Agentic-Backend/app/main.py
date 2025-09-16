from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import uvloop
import logging
import sys
from app.config import settings
from app.utils.logging import setup_logging
from app.api.middleware import LoggingMiddleware
from app.api.security_middleware import AgentSecurityMiddleware, RequestValidationMiddleware
from app.api.routes import api_router, ws_router
from app.utils.logging import get_logger
from app.db.database import check_database_health, engine

# Setup logging
setup_logging()
logger = get_logger("main")

# Configure event loop for optimal async performance
def configure_event_loop():
    """Configure event loop with optimal settings for async/SQLAlchemy compatibility."""
    try:
        # Use uvloop for better performance if available
        if sys.platform != 'win32':
            uvloop.install()
            logger.info("uvloop installed for enhanced async performance")
        
        # Get the current event loop
        loop = asyncio.get_event_loop()
        
        # Configure loop policies for better greenlet compatibility
        if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
            # Windows-specific optimization
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        elif hasattr(asyncio, 'DefaultEventLoopPolicy'):
            # Unix-specific optimization
            policy = asyncio.DefaultEventLoopPolicy()
            asyncio.set_event_loop_policy(policy)
            
    except Exception as e:
        logger.warning(f"Event loop configuration failed: {e}")

# Configure the event loop early
configure_event_loop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Enhanced application lifespan events with proper async resource management.
    
    This ensures database connections are properly initialized and cleaned up,
    preventing greenlet spawn errors during application lifecycle.
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Startup
    try:
        # Initialize database connection pool
        logger.info("Initializing database connection pool...")
        
        # Test database connectivity
        db_healthy = await check_database_health()
        if not db_healthy:
            logger.error("Database health check failed")
            raise RuntimeError("Database connection failed")
        
        logger.info("Database connection established successfully")
        
        # Store engine reference in app state for access
        app.state.db_engine = engine
        
        logger.info("Application startup complete")
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    finally:
        # Shutdown - Clean up database connections
        logger.info("Shutting down application...")
        
        try:
            # Dispose of database engine connections
            if hasattr(app.state, 'db_engine'):
                await app.state.db_engine.dispose()
                logger.info("Database connections disposed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local AI Agent Backend with Celery and Ollama Integration",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# CORS is now handled by nginx reverse proxy
# Removed CORSMiddleware to prevent duplicate headers

# Add custom middleware
app.add_middleware(LoggingMiddleware)

# Add security middleware (order matters - security should be early)
# Temporarily disabled to avoid initialization issues - will re-enable after testing
# app.add_middleware(AgentSecurityMiddleware)

# Include routers
app.include_router(api_router)
app.include_router(ws_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs_url": "/docs" if settings.debug else None
    }


# Simple health check endpoint (for load balancers/health checks)
@app.get("/health")
async def simple_health_check():
    """Simple health check endpoint for load balancers."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )