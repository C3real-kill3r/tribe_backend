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
    
    # Initialize database (create tables if they don't exist)
    # In production, use Alembic migrations instead
    # Always try to initialize database to ensure connection works
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # In production, we might want to continue anyway if using migrations
        # But for now, we'll raise to fail fast if DB is not available
        if not settings.debug:
            logger.warning(
                "Database initialization failed. If using Alembic migrations, "
                "ensure migrations are run separately. Continuing startup..."
            )
        else:
            raise
    
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
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
        "environment": settings.app_env,
        "timestamp": datetime.utcnow().isoformat()
    }


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

