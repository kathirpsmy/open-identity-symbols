"""
OIS Discovery Server — Phase 3

Self-hostable, password-free identity discovery.
Stores: symbol_id → { public_key_spki, alias, public_profile }
Auth:   WebAuthn assertion (proof-of-key).  No passwords, no sessions.

Runs on port 8001 by default (so it doesn't clash with the Phase 1 backend on 8000).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from discovery.config import settings
from discovery import database as _db
from discovery.api import admin, challenge, lookup, publish, search, self_delete


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup.
    # Accesses _db.engine at call time so tests can swap it out via patching.
    # For production use an Alembic migration instead of create_all.
    _db.Base.metadata.create_all(bind=_db.engine)
    yield


app = FastAPI(
    title       = "OIS Discovery Server",
    description = (
        "Open Identity Symbols — Phase 3 optional discovery server.\n\n"
        "Stores public identities so others can look them up by symbol or alias.\n"
        "Auth is entirely WebAuthn-based — no passwords, no email, no sessions."
    ),
    version     = "0.3.0",
    lifespan    = lifespan,
)

# CORS — allow the PWA (and any other static site) to call this API
origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins     = origins,
    allow_credentials = False,    # no cookies used
    allow_methods     = ["GET", "POST", "PUT", "DELETE"],
    allow_headers     = ["Content-Type", "Authorization"],
)

# Routes
app.include_router(challenge.router)
app.include_router(publish.router)
app.include_router(lookup.router)
app.include_router(search.router)
app.include_router(admin.router)
app.include_router(self_delete.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "ois-discovery", "version": "0.3.0"}


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "service": "OIS Discovery Server",
        "docs": "/docs",
        "endpoints": ["/challenge", "/publish", "/profile", "/lookup/{symbol_id}", "/lookup/alias/{alias}", "/lookup/key/{public_key_id}", "/lookup/credential/{credential_id}", "/search"],
    }
