from __future__ import annotations

import json
from typing import List, Optional, Union

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_auth_db
from app.core.security import Principal, STUB_USERS, decode_access_token
from app.models import User

bearer = HTTPBearer(auto_error=False)


def parse_portfolio_ids(raw: Optional[str]) -> Union[List[int], str]:
    if raw is None or raw == "":
        return []
    if raw == "ALL":
        return "ALL"
    try:
        data = json.loads(raw)
        if data == "ALL":
            return "ALL"
        return [int(x) for x in data]
    except (ValueError, TypeError):
        return []


def principal_from_user(user: User) -> Principal:
    return Principal(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        portfolio_ids=parse_portfolio_ids(user.portfolio_ids),
        full_name=user.full_name,
        status=user.status or "active",
    )


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    x_debug_role: Optional[str] = Header(default=None, alias="X-Debug-Role"),
    db: Session = Depends(get_auth_db),
) -> Principal:
    settings = get_settings()
    if settings.auth_mode == "stub":
        if settings.app_env == "prod":
            raise HTTPException(status_code=500, detail="stub auth forbidden")
        role = x_debug_role or "analyst"
        stub = STUB_USERS.get(role) or STUB_USERS["analyst"]
        return Principal(
            user_id=stub["user_id"],
            email=stub["email"],
            role=role,
            portfolio_ids=stub["allowed_portfolio_ids"],
        )
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "missing token"})
    try:
        claims = decode_access_token(creds.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "invalid token"})
    user = db.get(User, claims.get("sub"))
    if user is None or user.status != "active":
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "user inactive"})
    return principal_from_user(user)


def require_admin(user: Principal = Depends(get_current_user)) -> Principal:
    if not user.can_admin():
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "admin role required"})
    return user


def require_trace_role(user: Principal = Depends(get_current_user)) -> Principal:
    if not user.can_view_traces():
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "trace access denied"})
    return user
