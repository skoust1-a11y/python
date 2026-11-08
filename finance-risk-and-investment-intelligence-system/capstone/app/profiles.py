from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.constants import HOUSE_LABELS, HOUSE_TYPES, POLICY_DOCS
from app.core.ids import new_profile_id
from app.guardrails import has_advice_language
from app.models import Profile, ProfileGuideline

DEFAULT_PROFILE_ID = "default"
_PROF = re.compile(r"^prof_[a-zA-Z0-9]{8,}$")


def normalize_profile_id(value: Optional[str]) -> str:
    text = (value or "").strip() or DEFAULT_PROFILE_ID
    if text == DEFAULT_PROFILE_ID:
        return DEFAULT_PROFILE_ID
    if _PROF.fullmatch(text):
        return text
    return DEFAULT_PROFILE_ID


def default_profile() -> Dict[str, Any]:
    return {
        "profile_id": DEFAULT_PROFILE_ID,
        "name": "Default (original docs)",
        "kind": "default",
    }


def _out(row: Profile) -> Dict[str, Any]:
    return {"profile_id": row.profile_id, "name": row.name, "kind": "user"}


def list_profiles(db: Session, user_id: str) -> List[Dict[str, Any]]:
    rows = (
        db.query(Profile)
        .filter(Profile.user_id == user_id)
        .order_by(Profile.created_at.asc())
        .all()
    )
    return [default_profile()] + [_out(row) for row in rows]


def owned(db: Session, user_id: str, profile_id: Optional[str]) -> str:
    pid = normalize_profile_id(profile_id)
    if pid == DEFAULT_PROFILE_ID:
        return pid
    row = db.query(Profile).filter(Profile.profile_id == pid, Profile.user_id == user_id).first()
    if row is None:
        raise ValueError("unknown profile")
    return pid


def create_profile(db: Session, user_id: str, name: str) -> Dict[str, Any]:
    heading = (name or "").strip()[:80] or "Untitled"
    row = Profile(profile_id=new_profile_id(), user_id=user_id, name=heading)
    db.add(row)
    db.commit()
    return _out(row)


def delete_profile(db: Session, user_id: str, profile_id: str) -> bool:
    pid = normalize_profile_id(profile_id)
    if pid == DEFAULT_PROFILE_ID:
        raise ValueError("cannot delete the default profile")
    row = db.query(Profile).filter(Profile.profile_id == pid, Profile.user_id == user_id).first()
    if row is None:
        return False
    from app.rag import delete_profile_documents

    delete_profile_documents(user_id, pid)
    db.query(ProfileGuideline).filter(
        ProfileGuideline.user_id == user_id, ProfileGuideline.profile_id == pid
    ).delete(synchronize_session=False)
    db.delete(row)
    db.commit()
    return True


def guideline_text(db: Session, user_id: str, profile_id: str, use_case: str) -> str:
    row = (
        db.query(ProfileGuideline)
        .filter(
            ProfileGuideline.user_id == user_id,
            ProfileGuideline.profile_id == normalize_profile_id(profile_id),
            ProfileGuideline.use_case == use_case,
        )
        .first()
    )
    return (row.guideline_text or "").strip() if row else ""


def put_guideline(db: Session, user_id: str, profile_id: str, use_case: str, text: str) -> Dict[str, Any]:
    if use_case not in HOUSE_TYPES:
        raise ValueError("use case must be one of the seven house types")
    body = (text or "").strip()
    if not body:
        clear_guideline(db, user_id, profile_id, use_case)
        return {"use_case": use_case, "guideline_text": "", "guideline_source": "default"}
    if has_advice_language(body):
        raise ValueError("guideline cannot include buy, sell, hold, or target-price language")
    pid = normalize_profile_id(profile_id)
    row = (
        db.query(ProfileGuideline)
        .filter(
            ProfileGuideline.user_id == user_id,
            ProfileGuideline.profile_id == pid,
            ProfileGuideline.use_case == use_case,
        )
        .first()
    )
    if row is None:
        row = ProfileGuideline(
            user_id=user_id, profile_id=pid, use_case=use_case, guideline_text=body
        )
        db.add(row)
    else:
        row.guideline_text = body
        row.updated_at = datetime.utcnow()
    db.commit()
    return {"use_case": use_case, "guideline_text": body, "guideline_source": "yours"}


def clear_guideline(db: Session, user_id: str, profile_id: str, use_case: str) -> None:
    if use_case not in HOUSE_TYPES:
        raise ValueError("use case must be one of the seven house types")
    db.query(ProfileGuideline).filter(
        ProfileGuideline.user_id == user_id,
        ProfileGuideline.profile_id == normalize_profile_id(profile_id),
        ProfileGuideline.use_case == use_case,
    ).delete(synchronize_session=False)
    db.commit()


def type_setup(db: Session, user_id: str, profile_id: str) -> List[Dict[str, Any]]:
    from app.rag import user_document_records

    pid = normalize_profile_id(profile_id)
    mine = {
        row["use_case"]: row
        for row in user_document_records(user_id, pid)
        if row.get("use_case") in HOUSE_TYPES
    }
    rows = []
    for meta in POLICY_DOCS:
        uc = meta["use_case"]
        overlay = guideline_text(db, user_id, pid, uc)
        uploaded = mine.get(uc)
        pdf = uploaded or {
            "doc_id": meta["doc_id"],
            "doc_title": meta["doc_title"],
            "filename": meta["filename"],
            "origin": "system",
        }
        rows.append(
            {
                "use_case": uc,
                "label": HOUSE_LABELS[uc],
                "guideline_text": overlay,
                "guideline_source": "yours" if overlay else "default",
                "pdf": {
                    "doc_id": pdf["doc_id"],
                    "doc_title": pdf["doc_title"],
                    "filename": pdf["filename"],
                    "origin": pdf.get("origin", "system"),
                },
                "pdf_source": "yours" if uploaded else "default",
            }
        )
    return rows
