"""
Auth0 JWT Validation Middleware
-------------------------------
Validates RS256-signed JWTs issued by Auth0 before processing any agent request.

Flow:
  1. Extract Bearer token from the Authorization header.
  2. Download the JWKS (public keys) from Auth0's well-known endpoint.
  3. Match the token's kid to the correct public key.
  4. Decode and verify the token (audience, issuer, expiry).
  5. Return the decoded payload (contains sub, email, etc.).
"""

import requests
from typing import Optional
from jose import jwt, JWTError
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from settings.env_config import config
import functools

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

AUTH0_DOMAIN: Optional[str] = config.require_env("AUTH0_DOMAIN")
AUTH0_AUDIENCE: Optional[str] = config.require_env("AUTH0_AUDIENCE")
ALGORITHMS = ["RS256"]

security = HTTPBearer()

# ---------------------------------------------------------------------------
# JWKS fetching — cached so we don't hit Auth0 on every request
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Download and cache Auth0 JWKS public keys."""
    if not AUTH0_DOMAIN:
        raise HTTPException(status_code=500, detail="AUTH0_DOMAIN is not configured.")
    url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch JWKS from Auth0: {e}")


def _find_rsa_key(jwks: dict, kid: str) -> Optional[dict]:
    """Find the matching RSA public key from JWKS by key ID (kid)."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    return None


# ---------------------------------------------------------------------------
# JWT verification dependency
# ---------------------------------------------------------------------------

def verify_jwt(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """
    FastAPI dependency — validates the Auth0 JWT and returns the decoded payload.

    Usage:
        @router.post("/chat")
        def chat(request: ChatRequest, payload: dict = Depends(verify_jwt)):
            user_id = payload.get("sub")
    """
    if not AUTH0_DOMAIN or not AUTH0_AUDIENCE:
        raise HTTPException(
            status_code=500,
            detail="Auth0 is not configured on the server. Set AUTH0_DOMAIN and AUTH0_AUDIENCE.",
        )

    token = credentials.credentials

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token header.")

    jwks = _get_jwks()
    rsa_key = _find_rsa_key(jwks, unverified_header.get("kid", ""))

    if not rsa_key:
        # Invalidate cache and retry once (keys may have rotated)
        _get_jwks.cache_clear()
        jwks = _get_jwks()
        rsa_key = _find_rsa_key(jwks, unverified_header.get("kid", ""))

    if not rsa_key:
        raise HTTPException(status_code=401, detail="Unable to find a matching public key.")

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=ALGORITHMS,
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")


__all__ = ["verify_jwt"]
