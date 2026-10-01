from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.api.v1.agents import router as agents_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.policies import router as policies_router
from app.database.session import SessionLocal

app = FastAPI(
    title="Aegent",
    description="Security and Governance for Autonomous AI Agents",
    version="0.1.0",
)

app.include_router(auth_router, prefix='/api/v1')
app.include_router(agents_router, prefix='/api/v1')
app.include_router(policies_router, prefix='/api/v1')
app.include_router(approvals_router, prefix='/api/v1')
app.include_router(audit_router, prefix='/api/v1')


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
