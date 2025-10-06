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

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging
import time
import uuid
from collections import defaultdict
from app.db import Base, engine
from app import models   # must be imported before create_all to register tables
from app.routes import analyze, optimize, history, feedback, report, releases

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# STEP 2: Add middleware for security and logging
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Simple rate limiting (in production, use Redis or similar)
rate_limit_store = defaultdict(list)
from app.config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    now = time.time()
    
    # Clean old requests
    rate_limit_store[client_ip] = [
        req_time for req_time in rate_limit_store[client_ip] 
        if now - req_time < RATE_LIMIT_WINDOW
    ]
    
    # Check rate limit
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Add current request
    rate_limit_store[client_ip].append(now)
    
    return await call_next(request)

# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.info(f"[{request_id}] {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"[{request_id}] {response.status_code} - {process_time:.3f}s")
    
    return response

# STEP 3: Database initialization
# In production, run: alembic upgrade head
# For development, we can still use create_all as fallback
try:
    # Try to use Alembic if available
    from alembic import command
    from alembic.config import Config
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
except ImportError:
    # Alembic not installed, use create_all for development
    Base.metadata.create_all(bind=engine)
except Exception as e:
    # Alembic failed, fallback to create_all
    logger.warning(f"Alembic migration failed, using create_all: {e}")
    Base.metadata.create_all(bind=engine)

# STEP 4: Health check and metrics endpoints
@app.get("/health")
def health():
    """
    Simple health check endpoint.
    
    Returns: {"status": "ok"} if the service is running
    """
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    """
    Basic metrics endpoint for monitoring.
    
    Returns: Basic application metrics
    """
    from app.db import SessionLocal
    from app import models
    
    db = SessionLocal()
    try:
        prompt_count = db.query(models.Prompt).count()
        eval_count = db.query(models.Evaluation).count()
        suggestion_count = db.query(models.Suggestion).count()
        
        return {
            "prompts_total": prompt_count,
            "evaluations_total": eval_count,
            "suggestions_total": suggestion_count,
            "version": "0.3.0"
        }
    finally:
        db.close()

# STEP 4: Register all API route modules
# Each router provides a set of related endpoints
app.include_router(analyze.router,  prefix="/analyze",  tags=["analyze"])   # Core evaluation
app.include_router(optimize.router, prefix="/optimize", tags=["optimize"])  # Prompt optimization
app.include_router(history.router,  prefix="/history",  tags=["history"])   # Historical data
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])  # Human feedback
app.include_router(report.router,   prefix="/report",   tags=["report"])    # Analytics
app.include_router(releases.router, prefix="/prompts",  tags=["releases"])  # Canary management
