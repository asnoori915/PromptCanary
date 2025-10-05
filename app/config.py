import os
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL","postgresql+psycopg2://postgres:postgres@localhost:5432/promptpilot")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
CANARY_MIN_SAMPLES = int(os.getenv("CANARY_MIN_SAMPLES", "30"))
CANARY_THRESHOLD = float(os.getenv("CANARY_THRESHOLD", "0.55"))