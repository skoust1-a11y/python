from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import AuthSessionLocal, FinanceSessionLocal
from app.core.security import Principal
from app.models import AuditLog
from app.sqlq.templates import SlotError, TEMPLATES, UnknownTemplate


class RbacViolation(Exception):
    pass


def _validate(query_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    tmpl = TEMPLATES.get(query_id)
    if tmpl is None:
        raise UnknownTemplate(query_id)
    unknown = set(params) - set(tmpl.slots)
    if unknown:
        raise SlotError("unknown slots: {}".format(sorted(unknown)))
    bound: Dict[str, Any] = {}
    for name, slot in tmpl.slots.items():
        value = params.get(name, slot.default)
        if value is None:
            if slot.required and not slot.nullable:
                raise SlotError("missing slot {}".format(name))
            bound[name] = None
            continue
        if slot.kind == "int":
            value = int(value)
        elif slot.kind == "float":
            value = float(value)
        elif slot.kind == "str":
            value = str(value)
            if name in ("manager", "asset_name"):
                value = "%{}%".format(value.strip().lower())
        elif slot.kind == "enum":
            value = str(value)
            if slot.choices and value not in slot.choices:
                raise SlotError("invalid {}={!r}".format(name, value))
        if slot.minimum is not None and value < slot.minimum:
            raise SlotError("{} below min".format(name))
        if slot.maximum is not None and value > slot.maximum:
            raise SlotError("{} above max".format(name))
        bound[name] = value
    return bound


def _rbac_sql(rbac: str, principal: Principal) -> str:
    if rbac == "none" or principal.is_all_scope:
        return "1=1"
    ids = principal.allowed_ids()
    if not ids:
        return "1=0"
    joined = ",".join(str(int(i)) for i in ids)
    if rbac == "portfolio_id":
        return "portfolio_id IN ({})".format(joined)
    if rbac == "asset_via_holdings":
        return (
            "asset_name IN (SELECT asset_name FROM portfolio_holdings "
            "WHERE portfolio_id IN ({}))".format(joined)
        )
    return "1=0"


def _row_dict(row: Any) -> Dict[str, Any]:
    data = dict(row._mapping)
    for key, value in list(data.items()):
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
        elif hasattr(value, "__float__") and key in (
            "total_value",
            "market_value",
            "buy_price",
            "allocation_percentage",
            "indicator_value",
            "sector_allocation",
            "sector_value",
            "market_cap_cr",
            "pe",
            "pb",
            "roe",
            "roce",
            "debt_to_equity",
            "current_ratio",
            "sales_growth_3y",
            "profit_growth_3y",
            "dividend_yield",
            "promoter_holding",
        ):
            data[key] = float(value)
    return data


def run_template(
    query_id: str,
    params: Optional[Dict[str, Any]],
    principal: Principal,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    tmpl = TEMPLATES.get(query_id)
    if tmpl is None:
        raise UnknownTemplate(query_id)
    bound = _validate(query_id, params or {})
    sql = tmpl.sql.replace("{RBAC}", _rbac_sql(tmpl.rbac, principal))
    started = time.perf_counter()
    session = FinanceSessionLocal()
    try:
        rows = [_row_dict(r) for r in session.execute(text(sql), bound)]
    finally:
        session.close()
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if not principal.is_all_scope:
        allowed = set(principal.allowed_ids())
        for row in rows:
            pid = row.get("portfolio_id")
            if pid is not None and int(pid) not in allowed:
                raise RbacViolation("row outside authorized portfolio scope")
    auth = AuthSessionLocal()
    try:
        auth.add(
            AuditLog(
                trace_id=trace_id,
                query_id=query_id,
                role=principal.role,
                params_json=json.dumps(bound),
                row_count=len(rows),
                duration_ms=elapsed_ms,
            )
        )
        auth.commit()
    finally:
        auth.close()
    cap = get_settings().max_sql_rows
    truncated = rows[:cap]
    return {
        "query_id": query_id,
        "tables": tmpl.tables,
        "params": bound,
        "row_count": len(truncated),
        "rows": truncated,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
