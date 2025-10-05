"""
MAIN APPLICATION - FastAPI app initialization and configuration

This is the entry point for the PromptCanary application.
It sets up:
1. FastAPI app with metadata and documentation
2. Database table creation
3. Route registration for all API endpoints
4. Health check endpoint

The app provides a complete REST API for prompt evaluation, optimization,
canary deployments, and analytics.
"""

from fastapi import FastAPI
from app.db import Base, engine
from app import models   # must be imported before create_all to register tables
from app.routes import analyze, optimize, history, feedback, report, releases

# STEP 1: Create FastAPI application with metadata
app = FastAPI(
    title="PromptCanary",
    version="0.3.0",
    docs_url="/swagger",     # Interactive Swagger UI for API exploration
    redoc_url="/docs",       # Cleaner ReDoc documentation
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Hide schemas panel by default
        "defaultModelExpandDepth": -1,   # Collapse examples by default
    },
)

# STEP 2: Create database tables
# This creates all tables defined in models.py if they don't exist
# Note: In production, use Alembic migrations instead
Base.metadata.create_all(bind=engine)

# STEP 3: Health check endpoint
@app.get("/health")
def health():
    """
    Simple health check endpoint.
    
    Returns: {"status": "ok"} if the service is running
    """
    return {"status": "ok"}

# STEP 4: Register all API route modules
# Each router provides a set of related endpoints
app.include_router(analyze.router,  prefix="/analyze",  tags=["analyze"])   # Core evaluation
app.include_router(optimize.router, prefix="/optimize", tags=["optimize"])  # Prompt optimization
app.include_router(history.router,  prefix="/history",  tags=["history"])   # Historical data
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])  # Human feedback
app.include_router(report.router,   prefix="/report",   tags=["report"])    # Analytics
app.include_router(releases.router, prefix="/prompts",  tags=["releases"])  # Canary management
