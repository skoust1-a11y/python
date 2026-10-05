from __future__ import annotations

import csv
import io
import json
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    parse_portfolio_ids,
    principal_from_user,
    require_admin,
    require_trace_role,
)
from app.core.budget import budget_ok, rate_ok, record_cost
from app.core.config import get_settings
from app.core.constants import DISCLAIMER, POLICY_DOCS_BY_ID, ROLES
from app.core.db import AuthSessionLocal, FinanceSessionLocal, get_auth_db, get_finance_db
from app.core.ids import new_screen_id, new_user_id
from app.profiles import (
    clear_guideline,
    create_profile,
    delete_profile,
    list_profiles,
    owned as owned_profile,
    put_guideline,
    type_setup,
)
from app.core.security import Principal, create_access_token, hash_password, verify_password
from app.graph import CurrentFactorsOff, chat_title, run_query
from app.models import EscalationRecord, SavedScreen, ChatSession, TraceRecord, Turn, User
from app.rag import (
    DocumentIngestError,
    MAX_PDF_BYTES,
    chunk_count,
    chunks_for_doc,
    chunks_grouped,
    delete_user_document,
    embed_missing_chunks,
    embedded_count,
    ingest_user_pdf,
    pdf_path,
    reindex_from_pdfs,
    resolve_pdf,
    filing_counts,
    house_document_records,
    stock_document_records,
    document_meta,
)
from app.schemas import (
    AdminUserPatch,
    GuidelinePut,
    LoginRequest,
    ProfileCreate,
    QueryRequest,
    QueryResponse,
    ScreenNlRequest,
    ScreenSaveRequest,
    ScreenRunRequest,
    SessionRename,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    UserOut,
)
from app.screens import ScreenError, field_catalog, from_nl, run_screen
from app.sqlq.executor import RbacViolation, run_template
from app.sqlq.import_portfolio import (
    MAX_BYTES,
    PortfolioImportError,
    parse_holdings_csv,
    persist_uploaded_book,
)
from app.sqlq.templates import TEMPLATES, catalog

router = APIRouter()


def _user_out(user: User) -> UserOut:
    ids = parse_portfolio_ids(user.portfolio_ids)
    return UserOut(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        portfolio_ids=[] if ids == "ALL" else list(ids),
        full_name=user.full_name,
        status=user.status,
        features={"current_factors": get_settings().current_factors_enabled},
    )


def _principal_out(principal: Principal) -> UserOut:
    return UserOut(
        user_id=principal.user_id,
        email=principal.email,
        role=principal.role,
        portfolio_ids=[] if principal.is_all_scope else principal.allowed_ids(),
        full_name=principal.full_name,
        status=principal.status,
        features=principal.features(),
    )


@router.get("/health/ready", tags=["Health"])
def ready():
    """Readiness: database, vector index, LLM, and SQL templates."""
    checks: Dict[str, Any] = {}
    try:
        t0 = time.perf_counter()
        db = FinanceSessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        checks["database"] = {"ok": True, "latency_ms": int((time.perf_counter() - t0) * 1000)}
    except Exception as exc:  # noqa: BLE001
        checks["database"] = {"ok": False, "error": str(exc)}
    n = chunk_count()
    embedded = embedded_count()
    checks["vector_index"] = {"ok": n > 0, "chunk_count": n, "embedded": embedded}
    checks["llm"] = {"ok": True, "latency_ms": 0, "model": "deterministic"}
    checks["templates"] = {"ok": len(TEMPLATES) >= 18, "count": len(TEMPLATES)}
    ok = all(item.get("ok") for item in checks.values())
    status = 200 if ok else 503
    return Response(
        content=json.dumps({"status": "ready" if ok else "not_ready", "checks": checks}),
        media_type="application/json",
        status_code=status,
    )


@router.post("/api/v1/auth/signup", response_model=SignupResponse, tags=["Auth"])
def signup(body: SignupRequest, db: Session = Depends(get_auth_db)):
    """Register a new analyst account."""
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "email already registered"})
    user = User(
        user_id=new_user_id(),
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="analyst",
        portfolio_ids="[]",
        status="active",
    )
    db.add(user)
    db.commit()
    return SignupResponse(user_id=user.user_id, email=user.email, role=user.role)


def _login(body: LoginRequest, db: Session) -> TokenResponse:
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(body.password, user.password_hash) or user.status != "active":
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "invalid credentials"})
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    principal = principal_from_user(user)
    token = create_access_token(principal)
    return TokenResponse(
        access_token=token,
        expires_in=get_settings().session_ttl_minutes * 60,
        user=_user_out(user),
    )


@router.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(body: LoginRequest, db: Session = Depends(get_auth_db)):
    """Issue a JWT for an existing user."""
    return _login(body, db)


@router.post("/api/v1/auth/token", response_model=TokenResponse, tags=["Auth"])
def token_alias(body: LoginRequest, db: Session = Depends(get_auth_db)):
    """Login alias kept for compatibility (`/auth/token`)."""
    return _login(body, db)


@router.get("/api/v1/auth/me", response_model=UserOut, tags=["Auth"])
def me(user: Principal = Depends(get_current_user)):
    """Return the authenticated principal."""
    return _principal_out(user)


@router.get("/api/v1/profiles", tags=["Profiles"])
def profiles(user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """List analysis profiles for the caller."""
    return {"profiles": list_profiles(db, user.user_id)}


@router.post("/api/v1/profiles", tags=["Profiles"])
def add_profile(body: ProfileCreate, user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """Create an analysis profile."""
    return {"profile": create_profile(db, user.user_id, body.name)}


@router.delete("/api/v1/profiles/{profile_id}", tags=["Profiles"])
def remove_profile(profile_id: str, user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    try:
        if not delete_profile(db, user.user_id, profile_id):
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown profile"})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": str(exc)}) from exc
    return {"deleted": profile_id}


@router.get("/api/v1/profiles/{profile_id}/types", tags=["Profiles"])
def profile_types(profile_id: str, user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """Document-type setup for a profile."""
    try:
        pid = owned_profile(db, user.user_id, profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": str(exc)}) from exc
    return {"types": type_setup(db, user.user_id, pid), "disclaimer": DISCLAIMER}


@router.put("/api/v1/profiles/{profile_id}/guidelines/{use_case}", tags=["Profiles"])
def save_guideline(
    profile_id: str,
    use_case: str,
    body: GuidelinePut,
    user: Principal = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    """Replace a profile guideline for one use case."""
    try:
        pid = owned_profile(db, user.user_id, profile_id)
        return put_guideline(db, user.user_id, pid, use_case, body.guideline_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": str(exc)}) from exc


@router.delete("/api/v1/profiles/{profile_id}/guidelines/{use_case}", tags=["Profiles"])
def remove_guideline(
    profile_id: str,
    use_case: str,
    user: Principal = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    """Clear a profile guideline back to the default."""
    try:
        pid = owned_profile(db, user.user_id, profile_id)
        clear_guideline(db, user.user_id, pid, use_case)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": str(exc)}) from exc
    return {"use_case": use_case, "guideline_text": "", "guideline_source": "default"}


def _require_profile(user: Principal, profile_id: Optional[str]) -> str:
    db = AuthSessionLocal()
    try:
        return owned_profile(db, user.user_id, profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": str(exc)}) from exc
    finally:
        db.close()


@router.post("/api/v1/query", response_model=QueryResponse, tags=["Query"])
def query(
    body: QueryRequest,
    user: Principal = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    """Query the system with a natural-language finance question.

    Returns a grounded answer, refusal, or escalation with citations.
    """
    from app.models import IdempotencyKey

    if idempotency_key:
        db = AuthSessionLocal()
        try:
            cached = db.get(IdempotencyKey, idempotency_key)
            if cached and cached.user_id == user.user_id:
                return json.loads(cached.envelope_json)
        finally:
            db.close()
    if not rate_ok(user.user_id):
        raise HTTPException(status_code=429, detail={"code": "rate_limited", "message": "too many queries"})
    if not budget_ok(user.user_id):
        raise HTTPException(status_code=429, detail={"code": "budget_exceeded", "message": "daily budget exhausted"})
    body.options.profile_id = _require_profile(user, body.options.profile_id)
    try:
        result = run_query(user, body)
    except CurrentFactorsOff:
        raise HTTPException(
            status_code=409,
            detail={"code": "current_factors_unavailable", "message": "current factors are disabled"},
        )
    except RbacViolation as exc:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)})
    record_cost(user.user_id, result.cost_usd)
    payload = json.loads(result.model_dump_json())
    if idempotency_key:
        db = AuthSessionLocal()
        try:
            db.add(IdempotencyKey(key=idempotency_key, user_id=user.user_id, envelope_json=result.model_dump_json()))
            db.commit()
        finally:
            db.close()
    return payload


@router.post("/api/v1/query/stream", tags=["Query"])
def query_stream(body: QueryRequest, user: Principal = Depends(get_current_user)):
    """Same query as JSON, streamed as SSE progress and token events."""
    def events():
        if not rate_ok(user.user_id):
            yield "event: error\ndata: {\"code\":\"rate_limited\"}\n\n"
            return
        if not budget_ok(user.user_id):
            yield "event: error\ndata: {\"code\":\"budget_exceeded\"}\n\n"
            return
        try:
            body.options.profile_id = _require_profile(user, body.options.profile_id)
        except HTTPException as exc:
            yield "event: error\ndata: {}\n\n".format(json.dumps(exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}))
            return
        steps: "queue.Queue[Optional[str]]" = queue.Queue()
        outcome: Dict[str, Any] = {}

        def work() -> None:
            try:
                outcome["result"] = run_query(user, body, on_step=steps.put)
            except Exception as exc:  # noqa: BLE001 — re-raised or reported below
                outcome["error"] = exc
            finally:
                steps.put(None)

        threading.Thread(target=work, daemon=True).start()
        for node in iter(steps.get, None):
            yield "event: progress\ndata: {}\n\n".format(json.dumps({"node": node, "status": "complete"}))
        if isinstance(outcome.get("error"), CurrentFactorsOff):
            yield "event: error\ndata: {\"code\":\"current_factors_unavailable\"}\n\n"
            return
        if "error" in outcome:
            raise outcome["error"]
        result = outcome["result"]
        record_cost(user.user_id, result.cost_usd)
        routing = {
            "category": result.routing.category,
            "path": result.routing.path,
            "confidence": result.routing.confidence,
        }
        yield "event: routing\ndata: {}\n\n".format(json.dumps(routing))
        if result.outcome in ("escalated", "refused") or result.escalation.required:
            yield "event: escalation\ndata: {}\n\n".format(result.escalation.model_dump_json())
        else:
            for cite in result.citations:
                yield "event: citation\ndata: {}\n\n".format(cite.model_dump_json())
            yield "event: token\ndata: {}\n\n".format(json.dumps({"text": result.answer}))
        yield "event: done\ndata: {}\n\n".format(result.model_dump_json())

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/api/v1/sessions", tags=["Sessions"])
def list_sessions(user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """List recent chat sessions for the caller."""
    rows = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.user_id)
        .order_by(ChatSession.created_at.desc())
        .limit(50)
        .all()
    )
    sessions = []
    dirty = False
    for s in rows:
        title = (s.title or "").strip()
        if not title:
            first = (
                db.query(Turn.query)
                .filter(Turn.session_id == s.session_id)
                .order_by(Turn.turn_id.asc())
                .first()
            )
            title = chat_title(first[0]) if first and first[0] else "New chat"
            if first and first[0]:
                s.title = title
                dirty = True
        sessions.append(
            {
                "session_id": s.session_id,
                "title": title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )
    if dirty:
        db.commit()
    return {"sessions": sessions}


@router.delete("/api/v1/sessions", tags=["Sessions"])
def delete_all_sessions(user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """Delete every chat session owned by the caller."""
    ids = [row[0] for row in db.query(ChatSession.session_id).filter(ChatSession.user_id == user.user_id).all()]
    if ids:
        db.query(Turn).filter(Turn.session_id.in_(ids)).delete(synchronize_session=False)
        db.query(ChatSession).filter(ChatSession.session_id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    return {"deleted": len(ids)}


@router.patch("/api/v1/sessions/{session_id}", tags=["Sessions"])
def rename_session(
    session_id: str,
    body: SessionRename,
    user: Principal = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    """Rename a chat session."""
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown session"})
    if session.user_id != user.user_id and not user.can_admin():
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "not your session"})
    session.title = body.title
    db.commit()
    return {"session_id": session_id, "title": session.title}


@router.get("/api/v1/sessions/{session_id}/turns", tags=["Sessions"])
def session_turns(session_id: str, user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """Recent turns for follow-up context."""
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown session"})
    if session.user_id != user.user_id and not user.can_admin():
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "not your session"})
    turns = (
        db.query(Turn)
        .filter(Turn.session_id == session_id)
        .order_by(Turn.turn_id.desc())
        .limit(20)
        .all()
    )
    return {
        "session_id": session_id,
        "title": session.title or "New chat",
        "turns": [
            {
                "turn_id": t.turn_id,
                "query": t.query,
                "answer": t.answer,
                "outcome": t.outcome,
                "category": t.category,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in reversed(turns)
        ],
    }


@router.delete("/api/v1/sessions/{session_id}", tags=["Sessions"])
def delete_session(session_id: str, user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """End a session and purge its turns."""
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown session"})
    if session.user_id != user.user_id and not user.can_admin():
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "not your session"})
    db.query(Turn).filter(Turn.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"deleted": session_id}


@router.get("/api/v1/screens/fields", tags=["Screens"])
def screen_fields(_user: Principal = Depends(get_current_user)):
    """Whitelist of screenable equity fields."""
    return {"fields": field_catalog()}


def _with_doc_counts(result: Dict[str, Any], user: Principal, profile_id: Optional[str]) -> Dict[str, Any]:
    profile = _require_profile(user, profile_id)
    symbols = [str(row.get("symbol") or "") for row in result.get("rows") or []]
    counts = filing_counts(user.user_id, symbols, profile)
    for row in result.get("rows") or []:
        row["docs"] = counts.get(str(row.get("symbol") or "").upper(), 0)
    return result


@router.post("/api/v1/screens/run", tags=["Screens"])
def screens_run(
    body: ScreenRunRequest,
    profile_id: Optional[str] = None,
    user: Principal = Depends(get_current_user),
):
    """Run a stock-screen definition and return matching rows."""
    from app.core.ids import new_trace_id

    try:
        result = _with_doc_counts(run_screen(body.definition), user, profile_id)
    except ScreenError as exc:
        raise HTTPException(status_code=422, detail={"code": "unprocessable", "message": str(exc)})
    result["trace_id"] = new_trace_id()
    return result


@router.post("/api/v1/screens/from-nl", tags=["Screens"])
def screens_from_nl(
    body: ScreenNlRequest,
    profile_id: Optional[str] = None,
    user: Principal = Depends(get_current_user),
):
    """Turn a natural-language screen into a definition, optionally run it."""
    from app.core.ids import new_trace_id

    try:
        definition = from_nl(body.query)
        payload: Dict[str, Any] = {"definition": definition.model_dump(), "disclaimer": DISCLAIMER}
        if body.auto_run:
            payload.update(_with_doc_counts(run_screen(definition), user, profile_id))
        payload["trace_id"] = new_trace_id()
        return payload
    except ScreenError as exc:
        raise HTTPException(status_code=422, detail={"code": "unprocessable", "message": str(exc)})


@router.get("/api/v1/screens", tags=["Screens"])
def list_screens(
    profile_id: Optional[str] = None,
    user: Principal = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    """List saved screens for the active profile."""
    profile = _require_profile(user, profile_id)
    rows = db.query(SavedScreen).filter(SavedScreen.user_id == user.user_id, SavedScreen.profile_id == profile).all()
    return {
        "screens": [
            {
                "screen_id": s.screen_id,
                "name": s.name,
                "description": s.description,
                "definition": json.loads(s.definition),
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in rows
        ]
    }


@router.post("/api/v1/screens", tags=["Screens"])
def save_screen(
    body: ScreenSaveRequest,
    profile_id: Optional[str] = None,
    user: Principal = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    """Save a screen definition."""
    screen = SavedScreen(
        screen_id=new_screen_id(),
        user_id=user.user_id,
        profile_id=_require_profile(user, profile_id),
        name=body.name,
        description=body.description,
        definition=body.definition.model_dump_json(),
        is_public=body.is_public,
    )
    db.add(screen)
    db.commit()
    return {"screen_id": screen.screen_id, "name": screen.name}


def _owned_screen(db: Session, screen_id: str, user: Principal) -> SavedScreen:
    screen = db.get(SavedScreen, screen_id)
    if screen is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown screen"})
    if screen.user_id != user.user_id and not user.can_admin():
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "not your screen"})
    return screen


@router.get("/api/v1/screens/{screen_id}", tags=["Screens"])
def get_screen(screen_id: str, user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """Fetch one saved screen."""
    screen = _owned_screen(db, screen_id, user)
    return {
        "screen_id": screen.screen_id,
        "name": screen.name,
        "description": screen.description,
        "definition": json.loads(screen.definition),
    }


@router.put("/api/v1/screens/{screen_id}", tags=["Screens"])
def put_screen(
    screen_id: str,
    body: ScreenSaveRequest,
    user: Principal = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    """Replace a saved screen."""
    screen = _owned_screen(db, screen_id, user)
    screen.name = body.name
    screen.description = body.description
    screen.definition = body.definition.model_dump_json()
    screen.is_public = body.is_public
    screen.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"screen_id": screen.screen_id}


@router.delete("/api/v1/screens/{screen_id}", tags=["Screens"])
def delete_screen(screen_id: str, user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """Delete a saved screen."""
    screen = _owned_screen(db, screen_id, user)
    db.delete(screen)
    db.commit()
    return {"deleted": screen_id}


@router.get("/api/v1/screens/{screen_id}/export.csv", tags=["Screens"])
def export_screen(screen_id: str, user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """Export screen results as CSV."""
    screen = _owned_screen(db, screen_id, user)
    from app.schemas import ScreenDefinition

    result = run_screen(ScreenDefinition.model_validate(json.loads(screen.definition)))
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=result["columns"])
    writer.writeheader()
    for row in result["rows"]:
        writer.writerow(row)
    return Response(content=buf.getvalue(), media_type="text/csv")


@router.get("/api/v1/portfolios", tags=["Portfolios"])
def list_portfolios(user: Principal = Depends(get_current_user)):
    """List in-scope portfolios and holdings."""
    books = run_template("portfolios.all_in_scope", {"limit": 200}, user)
    holds = run_template("holdings.by_portfolio", {"limit": 200}, user)
    by_id: Dict[int, Dict[str, Any]] = {}
    for row in books["rows"]:
        pid = int(row["portfolio_id"])
        by_id[pid] = {**row, "holdings": []}
    for row in holds["rows"]:
        bucket = by_id.get(int(row["portfolio_id"]))
        if bucket is not None:
            bucket["holdings"].append(row)
    return {"portfolios": list(by_id.values()), "disclaimer": DISCLAIMER}


@router.post("/api/v1/portfolios/upload", tags=["Portfolios"])
def upload_portfolio(
    file: UploadFile = File(...),
    portfolio_name: str = Form(...),
    portfolio_manager: str = Form(""),
    risk_category: str = Form("Medium"),
    benchmark_index: str = Form(""),
    user: Principal = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
    finance: Session = Depends(get_finance_db),
):
    """Upload a holdings CSV and attach the new book to the caller."""
    db_user = db.get(User, user.user_id)
    if db_user is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_request", "message": "user record missing; cannot attach uploaded book"},
        )
    filename = (file.filename or "").lower()
    if filename and not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "upload a .csv file"})
    raw = file.file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "CSV is larger than 1MB"})
    try:
        text = raw.decode("utf-8-sig")
        rows = parse_holdings_csv(text)
        book = persist_uploaded_book(
            finance,
            name=portfolio_name,
            manager=portfolio_manager,
            risk=risk_category,
            benchmark=benchmark_index,
            rows=rows,
        )
    except (UnicodeDecodeError, PortfolioImportError) as exc:
        finance.rollback()
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": str(exc)}) from exc
    finance.commit()
    ids = parse_portfolio_ids(db_user.portfolio_ids)
    if ids != "ALL":
        merged = list(ids)
        if book.portfolio_id not in merged:
            merged.append(int(book.portfolio_id))
        db_user.portfolio_ids = json.dumps(merged)
        db.commit()
        ids = merged
    return {
        "portfolio": {
            "portfolio_id": book.portfolio_id,
            "portfolio_name": book.portfolio_name,
            "portfolio_manager": book.portfolio_manager,
            "risk_category": book.risk_category,
            "total_value": float(book.total_value or 0),
            "benchmark_index": book.benchmark_index,
            "holding_count": len(rows),
        },
        "portfolio_ids": [] if ids == "ALL" else list(ids),
        "disclaimer": DISCLAIMER,
    }


def _doc_listing(meta: Dict[str, Any], grouped: Dict[str, Any], owner_id: Optional[str]) -> Dict[str, Any]:
    parts = grouped.get(meta["doc_id"], [])
    return {
        **meta,
        "chunk_count": len(parts),
        "preview": (
            parts[0]["chunk_text"][: get_settings().citation_excerpt_chars] if parts else ""
        ),
        "has_file": resolve_pdf(meta["doc_id"], owner_id) is not None or (
            bool(meta.get("filename")) and pdf_path(str(meta["filename"])) is not None
        ),
    }


@router.get("/api/v1/documents", tags=["Documents"])
def documents(
    symbol: Optional[str] = None,
    profile_id: Optional[str] = None,
    user: Principal = Depends(get_current_user),
):
    """List policy documents, or filings for a symbol."""
    profile = _require_profile(user, profile_id)
    if symbol:
        listing = []
        for meta in stock_document_records(user.user_id, symbol, profile):
            parts = chunks_for_doc(meta["doc_id"])
            listing.append(
                {
                    **meta,
                    "chunk_count": len(parts),
                    "preview": parts[0]["chunk_text"][: get_settings().citation_excerpt_chars] if parts else "",
                    "has_file": resolve_pdf(meta["doc_id"], user.user_id) is not None,
                }
            )
        return {"documents": listing, "disclaimer": DISCLAIMER}
    grouped = chunks_grouped()
    listing = [_doc_listing(meta, grouped, user.user_id) for meta in house_document_records(user.user_id, profile)]
    return {"documents": listing, "disclaimer": DISCLAIMER}


@router.post("/api/v1/documents", tags=["Documents"])
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    use_case: str = Form("strategy"),
    symbol: str = Form(""),
    profile_id: str = Form("default"),
    user: Principal = Depends(get_current_user),
):
    """Ingest a user-uploaded PDF into the retrieval corpus."""
    filename = (file.filename or "").lower()
    if filename and not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "upload a .pdf file"})
    raw = file.file.read(MAX_PDF_BYTES + 1)
    if len(raw) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "PDF is larger than 5MB"})
    try:
        document = ingest_user_pdf(
            raw,
            file.filename or "upload.pdf",
            user.user_id,
            title,
            use_case,
            symbol,
            _require_profile(user, profile_id),
        )
    except DocumentIngestError as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": str(exc)}) from exc
    return {"document": document, "disclaimer": DISCLAIMER}


@router.get("/api/v1/documents/{doc_id}/file", tags=["Documents"])
def document_file(doc_id: str, user: Principal = Depends(get_current_user)):
    """Download the original PDF for a document."""
    meta = document_meta(doc_id, user.user_id)
    if not meta:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown document"})
    path = resolve_pdf(doc_id, user.user_id)
    if path is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "file not on disk"})
    return FileResponse(path, media_type="application/pdf", filename=meta.get("filename") or path.name)


@router.get("/api/v1/documents/{doc_id}", tags=["Documents"])
def get_document(doc_id: str, user: Principal = Depends(get_current_user)):
    """Document metadata and retrieved chunks."""
    meta = document_meta(doc_id, user.user_id)
    chunks = chunks_for_doc(doc_id) if meta else []
    if not meta:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown document"})
    return {
        "document": {**meta, "has_file": resolve_pdf(doc_id, user.user_id) is not None},
        "chunks": chunks,
        "disclaimer": DISCLAIMER,
    }


@router.delete("/api/v1/documents/{doc_id}", tags=["Documents"])
def remove_document(doc_id: str, user: Principal = Depends(get_current_user)):
    """Delete a user-uploaded document. Built-in policy docs cannot be removed."""
    if doc_id in POLICY_DOCS_BY_ID:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "built-in documents cannot be deleted"})
    if not delete_user_document(doc_id, user.user_id):
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown document"})
    return {"deleted": doc_id, "disclaimer": DISCLAIMER}


@router.get("/api/v1/escalations", tags=["Escalations"])
def list_escalations(user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """List escalations in the caller's scope."""
    q = db.query(EscalationRecord)
    if not user.can_view_all_escalations():
        q = q.filter(EscalationRecord.user_id == user.user_id)
    rows = q.order_by(EscalationRecord.created_at.desc()).limit(50).all()
    return {
        "escalations": [
            {
                "escalation_id": r.escalation_id,
                "trace_id": r.trace_id,
                "triggers": json.loads(r.triggers or "[]"),
                "reviewer": r.reviewer,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/api/v1/escalations/{escalation_id}", tags=["Escalations"])
def get_escalation(escalation_id: str, user: Principal = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """Full escalation envelope."""
    row = db.get(EscalationRecord, escalation_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown escalation"})
    if row.user_id != user.user_id and not user.can_view_all_escalations():
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "out of scope"})
    return json.loads(row.envelope_json or "{}")


@router.get("/api/v1/admin/users", tags=["Admin"])
def list_users(_admin: Principal = Depends(require_admin), db: Session = Depends(get_auth_db)):
    """Admin: list users so scope can be assigned by id."""
    return {"users": [_user_out(u) for u in db.query(User).order_by(User.email)]}


@router.patch("/api/v1/admin/users/{user_id}", tags=["Admin"])
@router.patch("/admin/users/{user_id}", tags=["Admin"])
def patch_user(user_id: str, body: AdminUserPatch, _admin: Principal = Depends(require_admin), db: Session = Depends(get_auth_db)):
    """Admin: set role, portfolio scope, or status."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown user"})
    if body.role is not None:
        if body.role not in ROLES:
            raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "bad role"})
        user.role = body.role
    if body.portfolio_ids is not None:
        user.portfolio_ids = json.dumps(body.portfolio_ids)
    if body.status is not None:
        if body.status not in ("active", "disabled"):
            raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "bad status"})
        user.status = body.status
    db.commit()
    return _user_out(user)


@router.post("/admin/reindex", tags=["Admin"])
def reindex(_admin: Principal = Depends(require_admin)):
    """Re-ingest the policy corpus and embed missing chunks."""
    added = reindex_from_pdfs()
    embedded = embed_missing_chunks()
    return {"reindexed": added, "embedded": embedded, "chunk_count": chunk_count(), "embedded_count": embedded_count()}


@router.get("/admin/traces/{trace_id}", tags=["Admin"])
def get_trace(trace_id: str, _user: Principal = Depends(require_trace_role), db: Session = Depends(get_auth_db)):
    """Span tree and evidence bundle for a past request."""
    row = db.get(TraceRecord, trace_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "unknown trace"})
    return {
        "trace_id": row.trace_id,
        "user_id": row.user_id,
        "session_id": row.session_id,
        "query": row.query,
        "category": row.category,
        "outcome": row.outcome,
        "spans": json.loads(row.spans_json or "{}"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/admin/templates", tags=["Admin"])
def admin_templates(_admin: Principal = Depends(require_admin)):
    """SQL template registry (ids, descriptions, slots)."""
    return {"templates": catalog()}


@router.get("/admin/eval/latest", tags=["Admin"])
def eval_latest(_admin: Principal = Depends(require_admin)):
    """Latest evaluation/SLO report, if the harness has been run."""
    from app.core.db import CAPSTONE_ROOT

    path = CAPSTONE_ROOT / "eval" / "reports" / "latest.json"
    if not path.is_file():
        return {"status": "none", "message": "eval harness not run yet"}
    return {"status": "ok", "report": json.loads(path.read_text(encoding="utf-8"))}
