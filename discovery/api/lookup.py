"""
GET /lookup/{symbol_id}        — look up an identity by its symbol triple.
GET /lookup/alias/{alias}      — look up an identity by its alias triple.
GET /lookup/key/{public_key_id} — look up by the SHA-256 key fingerprint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from discovery.database import get_db
from discovery.models import Identity
from discovery.schemas import IdentityPublic

router = APIRouter(prefix="/lookup", tags=["lookup"])


# Specific sub-paths MUST be declared before the greedy `/{symbol_id:path}` route
# otherwise FastAPI matches them to the symbol route first.

@router.get("/alias/{alias}", response_model=IdentityPublic)
def lookup_by_alias(alias: str, db: Session = Depends(get_db)) -> IdentityPublic:
    """Look up an identity by alias triple (e.g. `filth-satellite-camping`)."""
    identity = db.query(Identity).filter(Identity.alias == alias.lower()).first()
    if identity is None:
        raise HTTPException(404, f"Alias {alias!r} not found on this server")
    return identity


@router.get("/key/{public_key_id}", response_model=IdentityPublic)
def lookup_by_key_id(public_key_id: str, db: Session = Depends(get_db)) -> IdentityPublic:
    """Look up an identity by its public key fingerprint (SHA-256 hex)."""
    identity = db.get(Identity, public_key_id)
    if identity is None:
        raise HTTPException(404, f"Key fingerprint {public_key_id!r} not found on this server")
    return identity


@router.get("/credential/{credential_id}", response_model=IdentityPublic)
def lookup_by_credential(credential_id: str, db: Session = Depends(get_db)) -> IdentityPublic:
    """
    Look up an identity by WebAuthn credential ID (base64url).

    Used for cross-device recovery: the PWA calls assertPasskey() to get the
    credentialId back from the browser, then fetches this endpoint to retrieve
    the stored public_key_spki so symbols can be re-derived locally.
    """
    identity = db.query(Identity).filter(Identity.credential_id == credential_id).first()
    if identity is None:
        raise HTTPException(
            404,
            "Credential ID not found on this server. "
            "Make sure you are using the correct server URL and that you previously "
            "published your identity there.",
        )
    return identity


@router.get("/{symbol_id:path}", response_model=IdentityPublic)
def lookup_by_symbol(symbol_id: str, db: Session = Depends(get_db)) -> IdentityPublic:
    """
    Look up an identity by symbol_id (e.g. `⥐-📡-🏕`).

    Note: symbol_id contains Unicode characters so the path param uses `:path`
    to prevent URL encoding issues.  This route must be LAST in the router.
    """
    identity = db.query(Identity).filter(Identity.symbol_id == symbol_id).first()
    if identity is None:
        raise HTTPException(404, f"Symbol {symbol_id!r} not found on this server")
    return identity
