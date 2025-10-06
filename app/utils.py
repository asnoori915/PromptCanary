"""
UTILITIES - Shared functions and decorators

This module provides common utilities used across the application:
1. Database error handling decorator
2. Logging configuration
3. Common validation functions
4. Constants and configuration helpers
5. Type hints and common patterns
"""

import logging
import json
from functools import wraps
from typing import Callable, Any, Dict, Optional, Union
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

# Configure structured logging once for the entire app
def setup_logging():
    """Setup structured JSON logging."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    # Prevent duplicate logs
    logger.propagate = False

# Initialize logging
setup_logging()

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance with consistent formatting."""
    return logging.getLogger(name)

def handle_db_errors(func: Callable) -> Callable:
    """
    Decorator to handle database errors consistently across all routes.
    
    Usage:
    @handle_db_errors
    def my_route(db: Session = Depends(get_db)):
        # Your route logic here
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            logger = get_logger(func.__module__)
            logger.error(f"Database error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail="Database error")
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger = get_logger(func.__module__)
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper

def safe_db_commit(db: Session, *objects) -> None:
    """
    Safely commit database objects with proper error handling.
    
    Args:
        db: Database session
        *objects: SQLAlchemy objects to add and commit
    """
    try:
        for obj in objects:
            if obj is not None:
                db.add(obj)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

def safe_db_flush(db: Session, *objects) -> None:
    """
    Safely flush database objects with proper error handling.
    
    Args:
        db: Database session
        *objects: SQLAlchemy objects to add and flush
    """
    try:
        for obj in objects:
            if obj is not None:
                db.add(obj)
        db.flush()
    except Exception as e:
        db.rollback()
        raise e

# Constants
class Constants:
    """Application constants in one place."""
    
    # Rate limiting
    DEFAULT_RATE_LIMIT = 100  # requests per minute
    RATE_LIMIT_WINDOW = 60  # seconds
    
    # Analytics
    DEFAULT_WINDOW_DAYS = 30
    DEFAULT_MAX_COMPARE = 20
    
    # Canary settings
    DEFAULT_CANARY_THRESHOLD = 0.55
    DEFAULT_MIN_SAMPLES = 30
    
    # Validation limits
    MAX_PROMPT_LENGTH = 5000
    MAX_RESPONSE_LENGTH = 10000
    MAX_COMMENT_LENGTH = 1000
    MAX_MODEL_NAME_LENGTH = 64
    
    # Scoring
    OPTIMAL_PROMPT_LENGTH = 40
    VAGUENESS_PENALTY = 0.15
    
    # LLM settings
    DEFAULT_TEMPERATURE = 0.2
    DEFAULT_TIMEOUT = 30
    DEFAULT_MODEL = "gpt-4o-mini"

# Validation helpers
def validate_prompt_text(text: str) -> str:
    """Validate and clean prompt text."""
    if not text or not text.strip():
        raise ValueError("Prompt text cannot be empty")
    if len(text) > Constants.MAX_PROMPT_LENGTH:
        raise ValueError(f"Prompt text too long (max {Constants.MAX_PROMPT_LENGTH} chars)")
    return text.strip()

def validate_rating(rating: int) -> int:
    """Validate rating is in valid range."""
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5")
    return rating

def validate_percentage(percent: int) -> int:
    """Validate percentage is in valid range."""
    if not 0 <= percent <= 100:
        raise ValueError("Percentage must be between 0 and 100")
    return percent

# Utility functions
def get_current_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)

def round_score(score: float, decimals: int = 3) -> float:
    """Round score to specified decimal places."""
    return round(score, decimals)

def calculate_overall_score(scores: Dict[str, float]) -> float:
    """Calculate overall score from individual scores."""
    if not scores:
        return 0.0
    
    # Simple average - could be weighted in the future
    return sum(scores.values()) / len(scores)

def format_error_message(error: Exception) -> str:
    """Format error message for logging."""
    return f"{type(error).__name__}: {str(error)}"

# Type aliases for better readability
PromptText = str
ResponseText = str
ModelName = str
Score = float
Rating = int
Percentage = int
