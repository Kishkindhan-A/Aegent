from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.database.session import SessionLocal

app = FastAPI(
    title="Aegent",
    description="Security and Governance for Autonomous AI Agents",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "name": "Aegent",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.get("/health/database")
def database_health():
    try:
        with SessionLocal() as session:
            session.execute(text('SELECT 1'))
        return {
            "status": "healthy",
            "database": "reachable",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "unreachable",
                "message": "Database connection is unavailable.",
            },
        ) from exc
