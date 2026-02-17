import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import query, documents, workflows, auth, users, hr
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Enterprise AI Assistant",
    description="AI-Powered Enterprise Assistant with RAG and Workflow Automation",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(query.router)
app.include_router(documents.router)
app.include_router(workflows.router)
app.include_router(hr.router)


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


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Starting Enterprise AI Assistant...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Using Groq model: {settings.groq_model}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Shutting down Enterprise AI Assistant...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development"
    )
