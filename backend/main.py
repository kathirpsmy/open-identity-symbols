"""
Open Identity Symbols — FastAPI application entry point.

Start with:
    uvicorn backend.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.database import Base, engine
from backend.api.routes import auth, identity, profile, search

import backend.models  # noqa: F401 — ensures all models are registered with Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic migrations for production)
    Base.metadata.create_all(bind=engine)
    yield


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    lifespan=lifespan,
    title="Open Identity Symbols API",
    description="Privacy-first Unicode identity system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,     prefix="/api/v1")
app.include_router(identity.router, prefix="/api/v1")
app.include_router(profile.router,  prefix="/api/v1")
app.include_router(search.router,   prefix="/api/v1")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "open-identity-symbols"}
