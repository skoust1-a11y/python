"""Deterministic portfolio file parsing and validation.

Market prices are never fetched or inferred here. Symbol checks are format-only.
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from app.exceptions import PortfolioUploadError
from app.models.portfolio import (
    Holding,
    PortfolioFormat,
    PreviewHolding,
    SymbolValidation,
    ValidationIssue,
)
from app.models.types import normalize_currency, normalize_symbol

SUPPORTED_FORMATS: tuple[PortfolioFormat, ...] = ("csv", "xlsx")
XLSX_MAGIC = b"PK"

SYMBOL_ALIASES = {"symbol", "ticker", "instrument", "stock", "asset"}
QUANTITY_ALIASES = {"quantity", "qty", "shares", "units", "holding", "holdings"}
COST_ALIASES = {
    "average_cost",
    "avg_cost",
    "cost",
    "cost_basis",
    "purchase_price",
    "price",
    "avg_price",
}
WEIGHT_ALIASES = {"weight", "weight_pct", "allocation", "percent", "weight_percent"}
CURRENCY_ALIASES = {"currency", "ccy"}
NAME_ALIASES = {"name", "company", "asset_name", "security"}

CANONICAL_COLUMNS = {
    "symbol": SYMBOL_ALIASES,
    "quantity": QUANTITY_ALIASES,
    "average_cost": COST_ALIASES,
    "weight": WEIGHT_ALIASES,
    "currency": CURRENCY_ALIASES,
    "name": NAME_ALIASES,
}
REQUIRED_COLUMNS = ("symbol", "quantity")
WEIGHT_SUM_TOLERANCE = 0.02


@dataclass
class ParsedTable:
    headers: list[str]
    rows: list[dict[str, Any]]
    format: PortfolioFormat


@dataclass
class PortfolioParseResult:
    format: PortfolioFormat
    issues: list[ValidationIssue] = field(default_factory=list)
    holdings: list[PreviewHolding] = field(default_factory=list)
    importable: list[Holding] = field(default_factory=list)
    columns: dict[str, str] = field(default_factory=dict)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def can_confirm(self) -> bool:
        return not self.errors and bool(self.importable)


def issue(
    *,
    severity: str,
    code: str,
    message: str,
    row: int | None = None,
    column: str | None = None,
    value: Any = None,
) -> ValidationIssue:
    rendered = None if value is None else str(value)
    return ValidationIssue(
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=message,
        row=row,
        column=column,
        value=rendered,
    )


def validate_upload_file(
    *,
    filename: str | None,
    content: bytes,
    max_bytes: int,
) -> tuple[str, PortfolioFormat]:
    """Validate presence, size, and supported format. Does not parse rows."""
    issues: list[ValidationIssue] = []
    if filename is None or not str(filename).strip():
        issues.append(
            issue(
                severity="error",
                code="missing_file",
                message="A portfolio file is required.",
            )
        )
        raise PortfolioUploadError("A portfolio file is required.", issues=_dump_issues(issues))

    original_name = Path(str(filename).strip()).name
    if not original_name or original_name in {".", ".."}:
        issues.append(
            issue(
                severity="error",
                code="missing_file",
                message="A portfolio file is required.",
            )
        )
        raise PortfolioUploadError("A portfolio file is required.", issues=_dump_issues(issues))

    if not content:
        issues.append(
            issue(
                severity="error",
                code="empty_file",
                message="The uploaded file is empty.",
                value=original_name,
            )
        )
        raise PortfolioUploadError("The uploaded file is empty.", issues=_dump_issues(issues))

    if len(content) > max_bytes:
        issues.append(
            issue(
                severity="error",
                code="file_too_large",
                message=f"File exceeds the maximum size of {max_bytes} bytes.",
                value=str(len(content)),
            )
        )
        raise PortfolioUploadError(
            "The uploaded file is too large.",
            issues=_dump_issues(issues),
        )

    suffix = Path(original_name).suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_FORMATS:
        issues.append(
            issue(
                severity="error",
                code="unsupported_format",
                message="Supported portfolio formats are CSV and XLSX.",
                value=original_name,
            )
        )
        raise PortfolioUploadError(
            "Unsupported portfolio file format.",
            issues=_dump_issues(issues),
        )

    fmt: PortfolioFormat = "xlsx" if suffix == "xlsx" else "csv"
    looks_like_xlsx = content.startswith(XLSX_MAGIC)
    if fmt == "xlsx" and not looks_like_xlsx:
        issues.append(
            issue(
                severity="error",
                code="unreadable_file",
                message="The file extension is XLSX but the contents are not a valid spreadsheet.",
                value=original_name,
            )
        )
        raise PortfolioUploadError("The spreadsheet could not be read.", issues=_dump_issues(issues))
    if fmt == "csv" and looks_like_xlsx:
        issues.append(
            issue(
                severity="error",
                code="unreadable_file",
                message="The file extension is CSV but the contents look like a spreadsheet archive.",
                value=original_name,
            )
        )
        raise PortfolioUploadError("The CSV file could not be read.", issues=_dump_issues(issues))

    return original_name, fmt


def parse_portfolio_file(*, filename: str, content: bytes, fmt: PortfolioFormat) -> PortfolioParseResult:
    table = _read_table(filename=filename, content=content, fmt=fmt)
    return validate_parsed_table(table)


def validate_parsed_table(table: ParsedTable) -> PortfolioParseResult:
    result = PortfolioParseResult(format=table.format)
    mapping, mapping_issues = _map_columns(table.headers)
    result.columns = mapping
    result.issues.extend(mapping_issues)
    if any(col not in mapping for col in REQUIRED_COLUMNS):
        return result

    preview_rows: list[PreviewHolding] = []
    for index, raw_row in enumerate(table.rows):
        excel_row = index + 2
        if _row_is_empty(raw_row):
            result.issues.append(
                issue(
                    severity="warning",
                    code="empty_row",
                    message="Empty row skipped.",
                    row=excel_row,
                )
            )
            continue
        holding, row_issues = _validate_row(raw_row, mapping, excel_row)
        result.issues.extend(row_issues)
        preview_rows.append(holding)

    result.holdings = preview_rows
    _flag_duplicate_holdings(result)
    _flag_weight_and_currency(result)

    if not result.holdings:
        result.issues.append(
            issue(
                severity="error",
                code="no_holdings",
                message="The file does not contain any holdings.",
            )
        )

    if not result.errors:
        result.importable = [
            _to_holding(item) for item in result.holdings if item.valid and item.symbol
        ]
        if not result.importable:
            result.issues.append(
                issue(
                    severity="error",
                    code="no_holdings",
                    message="The file does not contain any importable holdings.",
                )
            )
    return result


def _dump_issues(issues: Iterable[ValidationIssue]) -> list[dict]:
    return [item.model_dump() for item in issues]


def _read_table(*, filename: str, content: bytes, fmt: PortfolioFormat) -> ParsedTable:
    try:
        if fmt == "csv":
            return _read_csv(content)
        return _read_xlsx(content)
    except PortfolioUploadError:
        raise
    except Exception as exc:
        raise PortfolioUploadError(
            "The portfolio file could not be parsed.",
            issues=_dump_issues(
                [
                    issue(
                        severity="error",
                        code="unreadable_file",
                        message="The file contents could not be parsed as a portfolio table.",
                        value=filename,
                    )
                ]
            ),
        ) from exc


def _read_csv(content: bytes) -> ParsedTable:
    text = _decode_csv(content)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [[cell.strip() if isinstance(cell, str) else cell for cell in row] for row in reader]
    return _table_from_matrix(rows, fmt="csv")


def _decode_csv(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = content.decode(encoding)
            if text.strip():
                return text
        except UnicodeDecodeError:
            continue
    raise PortfolioUploadError(
        "The CSV file could not be decoded.",
        issues=_dump_issues(
            [
                issue(
                    severity="error",
                    code="unreadable_file",
                    message="The CSV file is not valid UTF-8 or Windows text.",
                )
            ]
        ),
    )


def _read_xlsx(content: bytes) -> ParsedTable:
    from openpyxl import load_workbook

    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        sheet = workbook.active
        matrix: list[list[Any]] = []
        for row in sheet.iter_rows(values_only=True):
            matrix.append(list(row))
    finally:
        workbook.close()
    return _table_from_matrix(matrix, fmt="xlsx")


def _table_from_matrix(matrix: list[list[Any]], *, fmt: PortfolioFormat) -> ParsedTable:
    if not matrix:
        raise PortfolioUploadError(
            "The portfolio file has no rows.",
            issues=_dump_issues(
                [
                    issue(
                        severity="error",
                        code="no_holdings",
                        message="The file does not contain a header row.",
                    )
                ]
            ),
        )
    header_cells = matrix[0]
    headers = [_header_label(value, index) for index, value in enumerate(header_cells)]
    if len(headers) != len(set(headers)):
        raise PortfolioUploadError(
            "The portfolio file has duplicate column headers.",
            issues=_dump_issues(
                [
                    issue(
                        severity="error",
                        code="ambiguous_column",
                        message="Column headers must be unique.",
                    )
                ]
            ),
        )
    if not any(header.strip() for header in headers if isinstance(header, str)):
        raise PortfolioUploadError(
            "The portfolio file has no header row.",
            issues=_dump_issues(
                [
                    issue(
                        severity="error",
                        code="missing_column",
                        message="The first row must contain column headers.",
                    )
                ]
            ),
        )
    records: list[dict[str, Any]] = []
    for raw in matrix[1:]:
        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            record[header] = raw[index] if index < len(raw) else None
        records.append(record)
    while records and _row_is_empty(records[-1]):
        records.pop()
    return ParsedTable(headers=headers, rows=records, format=fmt)


def _header_label(value: Any, index: int) -> str:
    if value is None:
        return f"column_{index + 1}"
    text = str(value).strip()
    return text or f"column_{index + 1}"


def _normalize_header(value: str) -> str:
    return "_".join(value.strip().lower().replace("-", "_").split())


def _map_columns(headers: list[str]) -> tuple[dict[str, str], list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    normalized_to_original: dict[str, list[str]] = {}
    for header in headers:
        normalized_to_original.setdefault(_normalize_header(header), []).append(header)

    mapping: dict[str, str] = {}
    used_headers: set[str] = set()
    for canonical, aliases in CANONICAL_COLUMNS.items():
        matches: list[str] = []
        for alias in aliases:
            matches.extend(normalized_to_original.get(alias, []))
        unique_matches = list(dict.fromkeys(matches))
        if len(unique_matches) > 1:
            issues.append(
                issue(
                    severity="error",
                    code="ambiguous_column",
                    message=f"Multiple columns map to '{canonical}': {', '.join(unique_matches)}.",
                    column=canonical,
                )
            )
            continue
        if unique_matches:
            mapping[canonical] = unique_matches[0]
            used_headers.add(unique_matches[0])

    for required in REQUIRED_COLUMNS:
        if required not in mapping and not any(
            item.code == "ambiguous_column" and item.column == required for item in issues
        ):
            issues.append(
                issue(
                    severity="error",
                    code="missing_column",
                    message=f"Required column '{required}' is missing.",
                    column=required,
                )
            )

    for header in headers:
        if header in used_headers:
            continue
        if _normalize_header(header).startswith("column_"):
            continue
        issues.append(
            issue(
                severity="warning",
                code="unrecognized_column",
                message=f"Column '{header}' is not used during import.",
                column=header,
            )
        )
    return mapping, issues


def _row_is_empty(row: dict[str, Any]) -> bool:
    return all(_is_blank(value) for value in row.values())


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _validate_row(
    raw_row: dict[str, Any],
    mapping: dict[str, str],
    excel_row: int,
) -> tuple[PreviewHolding, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    raw_symbol = _raw_value(raw_row, mapping.get("symbol"))
    raw_quantity = _raw_value(raw_row, mapping.get("quantity"))

    symbol_validation, symbol, symbol_issues = _validate_symbol(raw_symbol, excel_row)
    issues.extend(symbol_issues)

    quantity, quantity_issues = _validate_quantity(raw_quantity, excel_row)
    issues.extend(quantity_issues)

    average_cost = None
    if "average_cost" in mapping:
        average_cost, cost_issues = _validate_optional_number(
            _raw_value(raw_row, mapping["average_cost"]),
            excel_row,
            column="average_cost",
            minimum=0,
            warn_if_blank=True,
        )
        issues.extend(cost_issues)

    weight = None
    if "weight" in mapping:
        weight, weight_issues = _validate_optional_number(
            _raw_value(raw_row, mapping["weight"]),
            excel_row,
            column="weight",
            minimum=0,
            allow_percent=True,
            warn_if_blank=True,
        )
        issues.extend(weight_issues)

    currency = None
    if "currency" in mapping:
        currency, currency_issues = _validate_optional_currency(
            _raw_value(raw_row, mapping["currency"]),
            excel_row,
            warn_if_blank=True,
        )
        issues.extend(currency_issues)

    name = None
    if "name" in mapping:
        name, name_issues = _validate_optional_name(
            _raw_value(raw_row, mapping["name"]),
            excel_row,
            warn_if_blank=True,
        )
        issues.extend(name_issues)

    valid = not any(item.severity == "error" for item in issues)
    preview = PreviewHolding(
        row=excel_row,
        symbol=symbol,
        quantity=quantity,
        average_cost=average_cost,
        currency=currency,
        name=name,
        weight=weight,
        symbol_validation=symbol_validation,
        valid=valid,
    )
    return preview, issues


def _raw_value(row: dict[str, Any], column: str | None) -> Any:
    if column is None:
        return None
    return row.get(column)


def _validate_symbol(value: Any, row: int) -> tuple[SymbolValidation, str | None, list[ValidationIssue]]:
    if _is_blank(value):
        validation = SymbolValidation(input=None, status="missing", reason="symbol is required")
        return (
            validation,
            None,
            [
                issue(
                    severity="error",
                    code="missing_value",
                    message="Symbol is required.",
                    row=row,
                    column="symbol",
                )
            ],
        )
    text = str(value).strip()
    try:
        normalized = normalize_symbol(text)
    except ValueError as exc:
        validation = SymbolValidation(
            input=text,
            status="invalid",
            reason=str(exc),
        )
        return (
            validation,
            None,
            [
                issue(
                    severity="error",
                    code="invalid_symbol",
                    message="Symbol must be a ticker or index code.",
                    row=row,
                    column="symbol",
                    value=text,
                )
            ],
        )
    validation = SymbolValidation(input=text, normalized=normalized, status="valid")
    return validation, normalized, []


def _validate_quantity(value: Any, row: int) -> tuple[float | None, list[ValidationIssue]]:
    if _is_blank(value):
        return None, [
            issue(
                severity="error",
                code="missing_value",
                message="Quantity is required.",
                row=row,
                column="quantity",
            )
        ]
    try:
        quantity = _parse_number(value)
    except ValueError:
        return None, [
            issue(
                severity="error",
                code="invalid_number",
                message="Quantity must be a finite number.",
                row=row,
                column="quantity",
                value=value,
            )
        ]
    if quantity <= 0:
        return None, [
            issue(
                severity="error",
                code="invalid_number",
                message="Quantity must be greater than 0.",
                row=row,
                column="quantity",
                value=value,
            )
        ]
    return quantity, []


def _validate_optional_number(
    value: Any,
    row: int,
    *,
    column: str,
    minimum: float,
    allow_percent: bool = False,
    warn_if_blank: bool = False,
) -> tuple[float | None, list[ValidationIssue]]:
    if _is_blank(value):
        if warn_if_blank:
            return None, [
                issue(
                    severity="warning",
                    code="missing_value",
                    message=f"{column.replace('_', ' ').capitalize()} is empty.",
                    row=row,
                    column=column,
                )
            ]
        return None, []
    try:
        number = _parse_number(value, allow_percent=allow_percent)
    except ValueError:
        return None, [
            issue(
                severity="error",
                code="invalid_number",
                message=f"{column.replace('_', ' ').capitalize()} must be a finite number.",
                row=row,
                column=column,
                value=value,
            )
        ]
    if number < minimum:
        return None, [
            issue(
                severity="error",
                code="invalid_number",
                message=f"{column.replace('_', ' ').capitalize()} must be greater than or equal to {minimum}.",
                row=row,
                column=column,
                value=value,
            )
        ]
    return number, []


def _validate_optional_currency(
    value: Any,
    row: int,
    *,
    warn_if_blank: bool = False,
) -> tuple[str | None, list[ValidationIssue]]:
    if _is_blank(value):
        if warn_if_blank:
            return None, [
                issue(
                    severity="warning",
                    code="missing_value",
                    message="Currency is empty.",
                    row=row,
                    column="currency",
                )
            ]
        return None, []
    text = str(value).strip()
    try:
        return normalize_currency(text), []
    except ValueError:
        return None, [
            issue(
                severity="error",
                code="invalid_currency",
                message="Currency must be a 3-letter ISO 4217 code.",
                row=row,
                column="currency",
                value=text,
            )
        ]


def _validate_optional_name(
    value: Any,
    row: int,
    *,
    warn_if_blank: bool = False,
) -> tuple[str | None, list[ValidationIssue]]:
    if _is_blank(value):
        if warn_if_blank:
            return None, [
                issue(
                    severity="warning",
                    code="missing_value",
                    message="Name is empty.",
                    row=row,
                    column="name",
                )
            ]
        return None, []
    text = str(value).strip()
    return (text or None), []


def _parse_number(value: Any, *, allow_percent: bool = False) -> float:
    if isinstance(value, bool) or isinstance(value, datetime):
        raise ValueError("invalid number")
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("invalid number")
        return number
    text = str(value).strip()
    if allow_percent:
        text = text.rstrip("%").strip()
    text = text.replace(",", "").replace("$", "").replace(" ", "")
    if not text:
        raise ValueError("invalid number")
    number = float(text)
    if not math.isfinite(number):
        raise ValueError("invalid number")
    return number


def _flag_duplicate_holdings(result: PortfolioParseResult) -> None:
    counts: dict[str, int] = {}
    for holding in result.holdings:
        if holding.symbol and holding.symbol_validation.status == "valid":
            counts[holding.symbol] = counts.get(holding.symbol, 0) + 1
    duplicates = {symbol for symbol, count in counts.items() if count > 1}
    if not duplicates:
        return
    updated: list[PreviewHolding] = []
    for holding in result.holdings:
        if holding.symbol in duplicates:
            result.issues.append(
                issue(
                    severity="error",
                    code="duplicate_holding",
                    message=f"Symbol {holding.symbol} appears more than once.",
                    row=holding.row,
                    column="symbol",
                    value=holding.symbol,
                )
            )
            updated.append(holding.model_copy(update={"valid": False}))
        else:
            updated.append(holding)
    result.holdings = updated


def _flag_weight_and_currency(result: PortfolioParseResult) -> None:
    provided_weights = [item.weight for item in result.holdings if item.weight is not None]
    if provided_weights:
        treat_as_percent = any(weight > 1 for weight in provided_weights)
        normalized: list[float] = []
        updated: list[PreviewHolding] = []
        for holding in result.holdings:
            weight = holding.weight
            if weight is None:
                updated.append(holding)
                continue
            converted = weight / 100.0 if treat_as_percent else weight
            if converted > 1:
                result.issues.append(
                    issue(
                        severity="error",
                        code="invalid_number",
                        message="Weight must be between 0 and 100 percent.",
                        row=holding.row,
                        column="weight",
                        value=holding.weight,
                    )
                )
                updated.append(holding.model_copy(update={"valid": False, "weight": None}))
                continue
            normalized.append(converted)
            updated.append(holding.model_copy(update={"weight": converted}))
        result.holdings = updated
        if normalized and abs(sum(normalized) - 1.0) > WEIGHT_SUM_TOLERANCE:
            result.issues.append(
                issue(
                    severity="warning",
                    code="weight_sum_mismatch",
                    message="Reported weights do not sum to 100%.",
                    column="weight",
                    value=round(sum(normalized), 6),
                )
            )

    currencies = {item.currency for item in result.holdings if item.currency}
    if len(currencies) > 1:
        result.issues.append(
            issue(
                severity="warning",
                code="mixed_currency",
                message="Holdings use more than one currency.",
                column="currency",
                value=",".join(sorted(currencies)),
            )
        )


def _to_holding(preview: PreviewHolding) -> Holding:
    if preview.symbol is None or preview.quantity is None:
        raise ValueError("cannot import an incomplete holding")
    try:
        return Holding(
            symbol=preview.symbol,
            quantity=preview.quantity,
            average_cost=preview.average_cost,
            currency=preview.currency,
            name=preview.name,
            weight=preview.weight,
            symbol_validation=preview.symbol_validation,
        )
    except ValidationError as exc:
        raise ValueError("holding failed normalized model validation") from exc
