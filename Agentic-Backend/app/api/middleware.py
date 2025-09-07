import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logging import get_logger
from app.utils.metrics import MetricsCollector

logger = get_logger("middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and collect metrics."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        # Process request
        response: Response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} - {duration:.3f}s",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": duration,
            }
        )
        
        # Collect metrics
        MetricsCollector.increment_api_requests(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        )
        
        return response


class CORSMiddleware:
    """Custom CORS middleware (if needed beyond FastAPI's built-in CORS)."""
    pass  # Use FastAPI's built-in CORSMiddleware instead