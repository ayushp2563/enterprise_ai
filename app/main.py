import logging
from contextlib import asynccontextmanager
import psycopg2
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.api import query, documents, workflows, auth, users, hr, conversations
from app.config import get_settings
from app.observability.logging import configure_logging
from app.observability.middleware import (
    InMemoryRateLimitMiddleware,
    RequestContextMiddleware,
)

configure_logging()

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info(
        "application_starting",
        extra={"environment": settings.environment},
    )
    yield
    logger.info("application_stopping")


# Create FastAPI app
app = FastAPI(
    title="Enterprise AI Assistant",
    description="AI-Powered Enterprise Assistant with RAG and Workflow Automation",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    InMemoryRateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
)
app.add_middleware(RequestContextMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(query.router)
app.include_router(documents.router)
app.include_router(workflows.router)
app.include_router(hr.router)
app.include_router(conversations.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Enterprise AI Assistant API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "enterprise-ai-assistant"
    }


@app.get("/ready")
async def readiness():
    """Verify dependencies required to serve API requests."""
    try:
        connection = psycopg2.connect(
            settings.database_url,
            connect_timeout=3,
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        connection.close()
        return {"status": "ready", "database": "available"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "database": "unavailable"},
        ) from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development"
    )
