"""
CONFIGURATION - Environment-based settings management

This file loads configuration from environment variables with sensible defaults.
It handles:
1. Database URL configuration (SQLite default, Postgres optional)
2. OpenAI API key for LLM integration
3. Webhook URL for notifications
4. Canary deployment thresholds and settings

All settings can be overridden via environment variables or .env file.
"""

import os
from dotenv import load_dotenv
from app.utils import Constants

# Load environment variables from .env file if it exists
load_dotenv()

# STEP 1: Database configuration
# Default to SQLite for simplicity, allow Postgres override
DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/promptcanary"
_raw_database_url = os.getenv("DATABASE_URL", "").strip()
DATABASE_URL = _raw_database_url or DEFAULT_DATABASE_URL

# STEP 2: External service configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")  # For LLM evaluation and optimization
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # For rollback notifications

# STEP 3: Canary deployment settings (using constants from utils)
CANARY_MIN_SAMPLES = int(os.getenv("CANARY_MIN_SAMPLES", str(Constants.DEFAULT_MIN_SAMPLES)))
CANARY_THRESHOLD = float(os.getenv("CANARY_THRESHOLD", str(Constants.DEFAULT_CANARY_THRESHOLD)))

# STEP 4: Rate limiting settings
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", str(Constants.DEFAULT_RATE_LIMIT)))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", str(Constants.RATE_LIMIT_WINDOW)))

# STEP 5: Analytics settings
DEFAULT_WINDOW_DAYS = int(os.getenv("DEFAULT_WINDOW_DAYS", str(Constants.DEFAULT_WINDOW_DAYS)))
DEFAULT_MAX_COMPARE = int(os.getenv("DEFAULT_MAX_COMPARE", str(Constants.DEFAULT_MAX_COMPARE)))