"""
Pytest configuration and fixtures.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app import models

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_promptcanary.db"

@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def sample_prompt(db_session):
    """Create a sample prompt for testing."""
    prompt = models.Prompt(text="Write a story about a robot")
    db_session.add(prompt)
    db_session.commit()
    db_session.refresh(prompt)
    return prompt

@pytest.fixture
def sample_response(db_session, sample_prompt):
    """Create a sample response for testing."""
    response = models.Response(
        prompt_id=sample_prompt.id,
        model_name="gpt-4o-mini",
        content="Once upon a time, there was a robot..."
    )
    db_session.add(response)
    db_session.commit()
    db_session.refresh(response)
    return response
