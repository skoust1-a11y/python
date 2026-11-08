from __future__ import annotations

import hashlib
import hmac
import json
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from app.core.config import get_settings


STUB_USERS = {
    "analyst": {"user_id": "u_analyst", "email": "analyst@local", "allowed_portfolio_ids": [1, 2]},
    "risk_manager": {"user_id": "u_risk", "email": "risk@local", "allowed_portfolio_ids": "ALL"},
    "compliance": {"user_id": "u_comp", "email": "compliance@local", "allowed_portfolio_ids": "ALL"},
    "admin": {"user_id": "u_admin", "email": "admin@local", "allowed_portfolio_ids": "ALL"},
}


class Principal:
    def __init__(
        self,
        user_id: str,
        email: str,
        role: str,
        portfolio_ids: Union[List[int], str],
        full_name: Optional[str] = None,
        status: str = "active",
    ) -> None:
        self.user_id = user_id
        self.email = email
        self.role = role
        self.portfolio_ids = portfolio_ids
        self.full_name = full_name
        self.status = status

    @property
    def is_all_scope(self) -> bool:
        return self.portfolio_ids == "ALL" or self.role in ("risk_manager", "compliance", "admin")

    def allowed_ids(self) -> List[int]:
        if self.is_all_scope:
            return []
        return list(self.portfolio_ids or [])

    def can_admin(self) -> bool:
        return self.role == "admin"

    def can_view_all_escalations(self) -> bool:
        return self.role in ("risk_manager", "compliance", "admin")

    def can_view_traces(self) -> bool:
        return self.role in ("admin", "compliance")

    def can_see_evidence_bundle(self) -> bool:
        return self.role in ("admin", "compliance")

    def features(self) -> Dict[str, bool]:
        return {"current_factors": get_settings().current_factors_enabled}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return "pbkdf2${}${}${}".format(200_000, salt.hex(), digest.hex())


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, rounds, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _b64encode(raw: bytes) -> str:
    return urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode(value + padding)


def create_access_token(principal: Principal) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": principal.user_id,
        "email": principal.email,
        "role": principal.role,
        "portfolio_ids": "ALL" if principal.is_all_scope else principal.allowed_ids(),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.session_ttl_minutes)).timestamp()),
    }
    header = _b64encode(json.dumps({"alg": settings.jwt_algorithm, "typ": "JWT"}).encode())
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = "{}.{}".format(header, body).encode("ascii")
    signature = hmac.new(settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return "{}.{}".format(signing_input.decode("ascii"), _b64encode(signature))


def decode_access_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        header_b64, body_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("invalid token") from exc
    signing_input = "{}.{}".format(header_b64, body_b64).encode("ascii")
    expected = hmac.new(settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64encode(expected), signature_b64):
        raise ValueError("invalid signature")
    payload = json.loads(_b64decode(body_b64))
    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("token expired")
    return payload


def principal_from_claims(claims: Dict[str, Any]) -> Principal:
    portfolio_ids = claims.get("portfolio_ids") or []
    return Principal(
        user_id=claims["sub"],
        email=claims.get("email") or "",
        role=claims.get("role") or "analyst",
        portfolio_ids=portfolio_ids,
    )
