from fastapi import FastAPI
from app.db import Base, engine
from app import models                    # <-- IMPORTANT: import models before create_all
from app.routes import analyze, optimize, history

app = FastAPI(title="PromptPilot", version="0.1.0")

# Create tables now that models are imported
Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(analyze.router,  prefix="/analyze",  tags=["analyze"])
app.include_router(optimize.router, prefix="/optimize", tags=["optimize"])
app.include_router(history.router,  prefix="/history",  tags=["history"])
