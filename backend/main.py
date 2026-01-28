from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import uvicorn
import logging
import traceback

from backend.routes import jobs, health, blockchain, statistics
from backend.database import init_db
from backend.exceptions import (
    BackendError,
    ValidationError,
    NotFoundError,
    DatabaseError,
    ServiceError,
    AlphaFoldError,
    DockingError,
    AIReportError,
    BlockchainError,
    FileProcessingError
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise
    yield
    # Shutdown: cleanup if needed
    logger.info("Application shutting down")

app = FastAPI(
    title="SNOWFLAKE API",
    description="AlphaFold-powered drug discovery and molecular docking platform",
    version="1.0.0",
    lifespan=lifespan
)

# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "message": "Request validation failed"
        }
    )

@app.exception_handler(ValidationError)
async def custom_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle custom validation errors"""
    logger.warning(f"Validation error on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.message,
            "message": "Validation failed",
            "details": exc.details
        }
    )

@app.exception_handler(NotFoundError)
async def not_found_exception_handler(request: Request, exc: NotFoundError):
    """Handle not found errors"""
    logger.info(f"Resource not found on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "message": "Resource not found",
            "details": exc.details
        }
    )

@app.exception_handler(DatabaseError)
async def database_exception_handler(request: Request, exc: DatabaseError):
    """Handle database errors"""
    logger.error(f"Database error on {request.url.path}: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database operation failed",
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(ServiceError)
async def service_exception_handler(request: Request, exc: ServiceError):
    """Handle service errors"""
    logger.error(f"Service error on {request.url.path}: {exc.message}", exc_info=True)
    
    # Map specific service errors to appropriate status codes
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, (AlphaFoldError, DockingError, AIReportError)):
        status_code = status.HTTP_502_BAD_GATEWAY  # Service unavailable
    elif isinstance(exc, BlockchainError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": exc.message,
            "message": "Service error",
            "details": exc.details,
            "error_type": exc.__class__.__name__
        }
    )

@app.exception_handler(FileProcessingError)
async def file_processing_exception_handler(request: Request, exc: FileProcessingError):
    """Handle file processing errors"""
    logger.error(f"File processing error on {request.url.path}: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.message,
            "message": "File processing failed",
            "details": exc.details
        }
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "detail": f"Endpoint not found: {request.url.path}",
            "message": "Resource not found"
        }
    )

@app.exception_handler(BackendError)
async def backend_exception_handler(request: Request, exc: BackendError):
    """Handle all backend errors"""
    logger.error(
        f"Backend error on {request.method} {request.url.path}: {exc.message}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": exc.message,
            "message": "Backend error",
            "details": exc.details,
            "error_type": exc.__class__.__name__
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "path": request.url.path
        }
    )

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(blockchain.router, prefix="/api", tags=["Blockchain"])
app.include_router(statistics.router, prefix="/api", tags=["Statistics"])
try:
    from backend.routes import external_api
    app.include_router(external_api.router, prefix="/api", tags=["External APIs"])
except ImportError:
    pass

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
