"""
Main FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.api.router import api_router
from app.db.session import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} API...")
    logger.info(f"Environment: {settings.app_env}, Debug: {settings.debug}")
    
    # Log database configuration (masked)
    from app.db.session import _mask_database_url
    masked_db_url = _mask_database_url(settings.database_url_async)
    logger.info(f"Database URL: {masked_db_url}")
    
    # Extract and log host/port for diagnostics
    try:
        if "@" in settings.database_url and ":" in settings.database_url.split("@")[1]:
            host_port = settings.database_url.split("@")[1].split("/")[0]
            logger.info(f"Database host/port: {host_port}")
    except Exception:
        pass  # Don't fail if URL parsing fails
    
    # Initialize database (create tables if they don't exist)
    # In production, use Alembic migrations instead
    # Try to initialize database, but don't fail startup if it's not available
    # This allows the app to start even if DB is temporarily unavailable
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        logger.warning(
            "Application will start, but database operations may fail. "
            "Please ensure:"
            "\n  1. DATABASE_URL environment variable is set correctly"
            "\n  2. Database service is running and accessible"
            "\n  3. Network connectivity between services is configured"
            "\n  4. If using Alembic migrations, ensure they are run separately"
        )
        # Don't raise - allow app to start and handle DB errors gracefully
        # The first API request will fail if DB is still unavailable, but at least
        # the app will be running and can recover when DB becomes available
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name} API...")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Backend API for the Tribe social accountability app",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url=f"/api/{settings.api_version}/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with consistent format."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    # Log the error in production
    if not settings.debug:
        # TODO: Log to Sentry or other error tracking
        pass
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred" if not settings.debug else str(exc)
        }
    )


# Include API router
app.include_router(api_router, prefix="/api")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    Includes database connectivity status.
    """
    from sqlalchemy import text
    from app.db.session import engine, _mask_database_url
    
    health_status = {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
        "environment": settings.app_env,
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "connected": False,
            "url": _mask_database_url(settings.database_url_async)
        }
    }
    
    # Test database connection
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["database"]["connected"] = True
    except Exception as e:
        health_status["database"]["error"] = str(e)
        health_status["status"] = "degraded"  # App is running but DB is not available
    
    return health_status


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else None,
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else 4
    )

