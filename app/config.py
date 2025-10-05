import os
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL","postgresql+psycopg2://postgres:postgres@localhost:5432/promptpilot")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")