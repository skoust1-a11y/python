from __future__ import annotations

import secrets
import uuid


def new_id(prefix: str) -> str:
    return "{}_{}".format(prefix, secrets.token_hex(8))


def new_user_id() -> str:
    return "u_{}".format(uuid.uuid4().hex[:16])


def new_session_id() -> str:
    return new_id("sess")


def new_trace_id() -> str:
    return new_id("trc")


def new_escalation_id() -> str:
    return new_id("esc")


def new_screen_id() -> str:
    return new_id("scr")


def new_doc_id() -> str:
    return new_id("udoc")


def new_profile_id() -> str:
    return new_id("prof")
