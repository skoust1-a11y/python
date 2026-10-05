from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from sqlalchemy import text

from app.core.constants import DISCLAIMER
from app.core.db import FinanceSessionLocal
from app.schemas import ScreenDefinition, ScreenFilter, ScreenSort

FIELDS = {
    "pe": {"type": "number", "column": "f.pe", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "pb": {"type": "number", "column": "f.pb", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "roe": {"type": "number", "column": "f.roe", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "roce": {"type": "number", "column": "f.roce", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "debt_to_equity": {"type": "number", "column": "f.debt_to_equity", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "current_ratio": {"type": "number", "column": "f.current_ratio", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "sales_growth_3y": {"type": "number", "column": "f.sales_growth_3y", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "profit_growth_3y": {"type": "number", "column": "f.profit_growth_3y", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "dividend_yield": {"type": "number", "column": "f.dividend_yield", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "promoter_holding": {"type": "number", "column": "f.promoter_holding", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "market_cap_cr": {"type": "number", "column": "u.market_cap_cr", "ops": ["eq", "ne", "gt", "gte", "lt", "lte", "between"]},
    "sector": {"type": "string", "column": "u.sector", "ops": ["eq", "ne", "in", "not_in"]},
    "industry": {"type": "string", "column": "u.industry", "ops": ["eq", "ne", "in", "not_in"]},
    "exchange": {"type": "string", "column": "u.exchange", "ops": ["eq", "ne", "in", "not_in"]},
    "symbol": {"type": "string", "column": "u.symbol", "ops": ["eq", "ne", "in", "not_in"]},
}

OPS_SQL = {
    "eq": "{col} = :{p}",
    "ne": "{col} <> :{p}",
    "gt": "{col} > :{p}",
    "gte": "{col} >= :{p}",
    "lt": "{col} < :{p}",
    "lte": "{col} <= :{p}",
}


class ScreenError(ValueError):
    pass


def field_catalog() -> List[Dict[str, Any]]:
    return [
        {"field": name, "type": spec["type"], "ops": spec["ops"]}
        for name, spec in FIELDS.items()
    ]


def _clause(filt: ScreenFilter, index: int) -> Tuple[str, Dict[str, Any]]:
    spec = FIELDS.get(filt.field)
    if spec is None:
        raise ScreenError("unknown field {}".format(filt.field))
    if filt.op not in spec["ops"] and filt.op not in ("is_null", "not_null"):
        raise ScreenError("op {} not allowed on {}".format(filt.op, filt.field))
    col = spec["column"]
    params: Dict[str, Any] = {}
    if filt.op in ("is_null", "not_null"):
        return ("{} IS NULL".format(col) if filt.op == "is_null" else "{} IS NOT NULL".format(col), params)
    if filt.op == "between":
        if not isinstance(filt.value, (list, tuple)) or len(filt.value) != 2:
            raise ScreenError("between needs [min, max]")
        lo, hi = "b{}_lo".format(index), "b{}_hi".format(index)
        params[lo] = filt.value[0]
        params[hi] = filt.value[1]
        return "{col} BETWEEN :{lo} AND :{hi}".format(col=col, lo=lo, hi=hi), params
    if filt.op in ("in", "not_in"):
        values = filt.value if isinstance(filt.value, list) else [filt.value]
        names = []
        for i, item in enumerate(values):
            key = "in{}_{}".format(index, i)
            params[key] = item
            names.append(":" + key)
        joiner = ", ".join(names) or "NULL"
        sql = "{col} IN ({vals})".format(col=col, vals=joiner)
        if filt.op == "not_in":
            sql = "NOT " + sql
        return sql, params
    key = "p{}".format(index)
    params[key] = filt.value
    return OPS_SQL[filt.op].format(col=col, p=key), params


def run_screen(definition: ScreenDefinition) -> Dict[str, Any]:
    clauses = []
    params: Dict[str, Any] = {}
    for i, filt in enumerate(definition.filters):
        sql, extra = _clause(filt, i)
        clauses.append(sql)
        params.update(extra)
    where = " AND ".join(clauses) if definition.logic == "and" else " OR ".join(clauses)
    if not where:
        where = "1=1"
    sort = definition.sort or [ScreenSort(field="roe", dir="desc")]
    order_parts = []
    for item in sort:
        spec = FIELDS.get(item.field)
        if spec is None:
            raise ScreenError("unknown sort field {}".format(item.field))
        order_parts.append("{} {}".format(spec["column"], "ASC" if item.dir == "asc" else "DESC"))
    sql = (
        "SELECT u.symbol, u.company_name, u.sector, u.industry, u.exchange, u.market_cap_cr, "
        "f.pe, f.pb, f.roe, f.roce, f.debt_to_equity, f.current_ratio, f.dividend_yield "
        "FROM equity_universe u JOIN equity_fundamentals f ON u.symbol = f.symbol "
        "WHERE u.is_active IS TRUE AND f.period_type = :period_type AND ({where}) "
        "ORDER BY {order} LIMIT :limit"
    ).format(where=where, order=", ".join(order_parts))
    params["period_type"] = definition.period.type
    params["limit"] = definition.limit
    session = FinanceSessionLocal()
    try:
        raw = session.execute(text(sql), params)
        columns = list(raw.keys())
        rows = []
        for row in raw:
            item = dict(row._mapping)
            for key, value in list(item.items()):
                if hasattr(value, "__float__") and value is not None and key != "symbol":
                    try:
                        item[key] = float(value)
                    except (TypeError, ValueError):
                        pass
            rows.append(item)
    finally:
        session.close()
    return {
        "row_count": len(rows),
        "columns": columns,
        "rows": rows,
        "definition_echo": definition.model_dump(),
        "citations": [
            {
                "type": "sql",
                "tables": ["equity_universe", "equity_fundamentals"],
                "query_id": "screen.run",
                "rows": len(rows),
            }
        ],
        "disclaimer": DISCLAIMER,
    }


_NUM = re.compile(
    r"(roe|roce|pe|pb|debt(?:/| to )?equity|market cap)\s*(>|>=|<|<=|=)\s*([0-9.]+)",
    re.I,
)
_FIELD_ALIASES = {
    "roe": "roe",
    "roce": "roce",
    "pe": "pe",
    "pb": "pb",
    "debt/equity": "debt_to_equity",
    "debt to equity": "debt_to_equity",
    "market cap": "market_cap_cr",
}
_OP_ALIASES = {">": "gt", ">=": "gte", "<": "lt", "<=": "lte", "=": "eq"}
_SECTORS = ["Technology", "Healthcare", "Finance", "Energy", "Consumer"]


def from_nl(query: str) -> ScreenDefinition:
    filters: List[ScreenFilter] = []
    for match in _NUM.finditer(query):
        field = _FIELD_ALIASES[match.group(1).lower().replace("  ", " ")]
        filters.append(ScreenFilter(field=field, op=_OP_ALIASES[match.group(2)], value=float(match.group(3))))
    for sector in _SECTORS:
        if re.search(r"\b{}\b".format(re.escape(sector)), query, re.I) or (
            sector == "Technology" and re.search(r"\b(it|tech)\b", query, re.I)
        ):
            filters.append(ScreenFilter(field="sector", op="eq", value=sector))
    if not filters:
        raise ScreenError("could not parse a screen from that text")
    return ScreenDefinition(filters=filters, sort=[ScreenSort(field="roe", dir="desc")], limit=50)
