import os
from dotenv import load_dotenv
load_dotenv()
DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/promptcanary"
_raw_database_url = os.getenv("DATABASE_URL", "").strip()
DATABASE_URL = _raw_database_url or DEFAULT_DATABASE_URL
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
CANARY_MIN_SAMPLES = int(os.getenv("CANARY_MIN_SAMPLES", "30"))
CANARY_THRESHOLD = float(os.getenv("CANARY_THRESHOLD", "0.55"))