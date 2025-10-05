"""
DATABASE CONFIGURATION - SQLAlchemy setup and session management

This file configures the database connection and provides session management.
It sets up:
1. Database engine with connection pooling
2. Session factory for creating database sessions
3. Base class for all ORM models
4. Dependency injection function for FastAPI routes

The get_db() function is used as a FastAPI dependency to provide
database sessions to route handlers.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

# STEP 1: Create database engine with connection pooling
# pool_pre_ping=True ensures connections are validated before use
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# STEP 2: Create session factory
# autocommit=False, autoflush=False for explicit transaction control
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# STEP 3: Create base class for all ORM models
Base = declarative_base()

def get_db():
    """
    FastAPI dependency for database sessions.
    
    This function provides a database session to route handlers.
    It ensures the session is properly closed after the request completes.
    
    Usage in routes:
    def my_route(db: Session = Depends(get_db)):
        # Use db session here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()