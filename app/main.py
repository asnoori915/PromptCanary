from fastapi import FastAPI
from app.db import Base, engine
from app import models   # must be before create_all
from app.routes import analyze, optimize, history, feedback, report

app = FastAPI(title="PromptPilot", version="0.3.0")

Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(analyze.router,  prefix="/analyze",  tags=["analyze"])
app.include_router(optimize.router, prefix="/optimize", tags=["optimize"])
app.include_router(history.router,  prefix="/history",  tags=["history"])
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
app.include_router(report.router,   prefix="/report",   tags=["report"])
