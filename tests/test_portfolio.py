"""Portfolio upload, validation, preview, confirm, and persistence tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.exceptions import PortfolioUploadError
from app.main import create_app
from app.models.portfolio import Holding, Portfolio, SymbolValidation
from app.tools.portfolio import parse_portfolio_file, validate_upload_file
from tests.helpers import csv_bytes, make_settings, xlsx_bytes

VALID_HEADERS = ["symbol", "quantity", "average_cost", "currency"]
VALID_ROWS = [
    ["AAPL", "10", "190.25", "USD"],
    ["MSFT", "5", "420.00", "USD"],
]


def _upload(client: TestClient, filename: str, content: bytes, content_type: str = "text/csv"):
    return client.post(
        "/portfolios/uploads",
        files={"file": (filename, content, content_type)},
    )


def test_validate_upload_file_rejects_empty_and_oversized_content() -> None:
    with pytest.raises(PortfolioUploadError) as empty:
        validate_upload_file(filename="holdings.csv", content=b"", max_bytes=100)
    assert empty.value.issues[0]["code"] == "empty_file"

    with pytest.raises(PortfolioUploadError) as large:
        validate_upload_file(filename="holdings.csv", content=b"x" * 20, max_bytes=10)
    assert large.value.issues[0]["code"] == "file_too_large"

    with pytest.raises(PortfolioUploadError) as fmt:
        validate_upload_file(filename="holdings.pdf", content=b"%PDF", max_bytes=1000)
    assert fmt.value.issues[0]["code"] == "unsupported_format"


def test_parser_accepts_csv_aliases_and_normalizes_symbols() -> None:
    content = csv_bytes(
        ["Ticker", "Shares", "Avg Cost"],
        [["aapl", "10", "$1,190.25"], ["brk.b", "2", "400"]],
    )
    parsed = parse_portfolio_file(filename="holdings.csv", content=content, fmt="csv")
    assert parsed.can_confirm
    assert [item.symbol for item in parsed.importable] == ["AAPL", "BRK.B"]
    assert parsed.importable[0].average_cost == 1190.25
    assert parsed.importable[0].symbol_validation.status == "valid"


def test_parser_rejects_missing_columns_invalid_numbers_and_duplicates() -> None:
    missing = parse_portfolio_file(
        filename="holdings.csv",
        content=csv_bytes(["name"], [["Apple"]]),
        fmt="csv",
    )
    assert {item.code for item in missing.errors} >= {"missing_column"}
    assert not missing.can_confirm

    numeric = parse_portfolio_file(
        filename="holdings.csv",
        content=csv_bytes(["symbol", "quantity"], [["AAPL", "ten"], ["MSFT", "-1"]]),
        fmt="csv",
    )
    assert all(item.code == "invalid_number" for item in numeric.errors)
    assert not numeric.can_confirm

    duplicates = parse_portfolio_file(
        filename="holdings.csv",
        content=csv_bytes(["symbol", "quantity"], [["AAPL", "1"], ["aapl", "2"]]),
        fmt="csv",
    )
    assert any(item.code == "duplicate_holding" for item in duplicates.errors)
    assert not duplicates.can_confirm


def test_parser_detects_missing_values_and_invalid_symbols() -> None:
    parsed = parse_portfolio_file(
        filename="holdings.csv",
        content=csv_bytes(
            ["symbol", "quantity", "average_cost"],
            [["", "10", ""], ["AAPL US", "5", "10"], ["MSFT", "", "11"]],
        ),
        fmt="csv",
    )
    codes = {item.code for item in parsed.issues}
    assert "missing_value" in codes
    assert "invalid_symbol" in codes
    assert parsed.holdings[1].symbol_validation.status == "invalid"
    assert not parsed.can_confirm


def test_normalized_portfolio_model_rejects_duplicates() -> None:
    validation = SymbolValidation(input="AAPL", normalized="AAPL", status="valid")
    holding = Holding(symbol="AAPL", quantity=1, symbol_validation=validation)
    with pytest.raises(ValidationError):
        Portfolio(
            id="p1",
            holdings=[holding, holding],
            source_filename="holdings.csv",
            source_format="csv",
            imported_at=datetime.now(timezone.utc),
        )


def test_valid_csv_upload_preview_confirm_makes_portfolio_available(client: TestClient) -> None:
    listed = client.get("/portfolios")
    assert listed.status_code == 200
    assert listed.json() == []

    response = _upload(client, "holdings.csv", csv_bytes(VALID_HEADERS, VALID_ROWS))
    assert response.status_code == 200
    preview = response.json()
    assert preview["status"] == "valid"
    assert preview["can_confirm"] is True
    assert preview["holding_count"] == 2
    assert preview["format"] == "csv"
    assert preview["issues"] == []
    assert preview["holdings"][0]["symbol"] == "AAPL"
    assert preview["holdings"][0]["symbol_validation"]["status"] == "valid"
    upload_id = preview["upload_id"]

    assert client.get("/portfolios").json() == []
    replay = client.get(f"/portfolios/uploads/{upload_id}")
    assert replay.status_code == 200
    assert replay.json()["upload_id"] == upload_id

    confirmed = client.post(
        f"/portfolios/uploads/{upload_id}/confirm",
        json={"name": "Core holdings"},
    )
    assert confirmed.status_code == 200
    portfolio = confirmed.json()
    assert portfolio["status"] == "imported"
    assert portfolio["name"] == "Core holdings"
    assert portfolio["holding_count"] == 2
    assert portfolio["holdings"][0]["cost_value"] == pytest.approx(1902.5)
    portfolio_id = portfolio["id"]

    available = client.get(f"/portfolios/{portfolio_id}")
    assert available.status_code == 200
    assert available.json()["id"] == portfolio_id
    assert available.json()["holdings"][0]["symbol"] == "AAPL"

    summary = client.get(f"/portfolios/{portfolio_id}/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["id"] == portfolio_id
    assert body["holding_count"] == 2
    assert body["status"] == "imported"
    assert body["base_currency"] == "USD"
    assert "holdings" not in body

    holdings = client.get(f"/portfolios/{portfolio_id}/holdings")
    assert holdings.status_code == 200
    listed_holdings = holdings.json()
    assert listed_holdings["portfolio_id"] == portfolio_id
    assert listed_holdings["holding_count"] == 2
    assert [row["symbol"] for row in listed_holdings["holdings"]] == ["AAPL", "MSFT"]
    assert listed_holdings["holdings"][0]["symbol_validation"]["status"] == "valid"

    summaries = client.get("/portfolios")
    assert summaries.status_code == 200
    assert summaries.json()[0]["id"] == portfolio_id
    assert summaries.json()[0]["holding_count"] == 2
    assert "holdings" not in summaries.json()[0]

    second = client.post(f"/portfolios/uploads/{upload_id}/confirm")
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "portfolio_import_error"


def test_valid_xlsx_upload_can_be_confirmed(client: TestClient) -> None:
    content = xlsx_bytes(["instrument", "qty", "currency"], [["msft", 3, "usd"], ["GOOG", 1, "USD"]])
    response = _upload(
        client,
        "holdings.xlsx",
        content,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert response.status_code == 200
    preview = response.json()
    assert preview["format"] == "xlsx"
    assert preview["can_confirm"] is True
    assert [row["symbol"] for row in preview["holdings"]] == ["MSFT", "GOOG"]

    confirmed = client.post(f"/portfolios/uploads/{preview['upload_id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["source_format"] == "xlsx"
    assert confirmed.json()["base_currency"] == "USD"


def test_file_too_large_returns_structured_error() -> None:
    application = create_app(make_settings(app_env="test", portfolio_max_upload_bytes=16))
    with TestClient(application) as client:
        response = _upload(client, "holdings.csv", csv_bytes(VALID_HEADERS, VALID_ROWS))
    assert response.status_code == 400
    body = response.json()["error"]
    assert body["code"] == "portfolio_upload_error"
    assert body["issues"][0]["code"] == "file_too_large"


def test_unsupported_and_unreadable_files_return_structured_errors(client: TestClient) -> None:
    pdf = _upload(client, "notes.pdf", b"%PDF-1.4 fake", "application/pdf")
    assert pdf.status_code == 400
    assert pdf.json()["error"]["issues"][0]["code"] == "unsupported_format"

    fake_xlsx = _upload(client, "holdings.xlsx", b"not-a-spreadsheet", "application/octet-stream")
    assert fake_xlsx.status_code == 400
    assert fake_xlsx.json()["error"]["issues"][0]["code"] == "unreadable_file"


def test_invalid_csv_returns_preview_with_errors_and_cannot_be_confirmed(client: TestClient) -> None:
    response = _upload(
        client,
        "holdings.csv",
        csv_bytes(
            ["symbol", "quantity"],
            [["AAPL", ""], ["AAPL US", "abc"], ["AAPL", "2"], ["", "3"]],
        ),
    )
    assert response.status_code == 200
    preview = response.json()
    assert preview["status"] == "invalid"
    assert preview["can_confirm"] is False
    codes = {issue["code"] for issue in preview["issues"]}
    assert {"missing_value", "invalid_number", "invalid_symbol", "duplicate_holding"} <= codes

    blocked = client.post(f"/portfolios/uploads/{preview['upload_id']}/confirm")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "portfolio_import_error"
    assert client.get("/portfolios").json() == []


def test_missing_required_columns_are_reported(client: TestClient) -> None:
    response = _upload(client, "holdings.csv", csv_bytes(["company", "weight"], [["Apple", "1"]]))
    assert response.status_code == 200
    codes = [issue["code"] for issue in response.json()["issues"] if issue["severity"] == "error"]
    assert codes.count("missing_column") == 2
    assert response.json()["can_confirm"] is False


def test_warnings_do_not_block_confirm(client: TestClient) -> None:
    response = _upload(
        client,
        "holdings.csv",
        csv_bytes(
            ["symbol", "quantity", "average_cost", "sector"],
            [["AAPL", "1", "", "tech"], ["MSFT", "2", "10", "tech"]],
        ),
    )
    assert response.status_code == 200
    preview = response.json()
    assert preview["status"] == "valid_with_warnings"
    assert preview["can_confirm"] is True
    warning_codes = {issue["code"] for issue in preview["issues"] if issue["severity"] == "warning"}
    assert "missing_value" in warning_codes
    assert "unrecognized_column" in warning_codes

    confirmed = client.post(f"/portfolios/uploads/{preview['upload_id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "imported"


def test_unknown_upload_and_portfolio_are_not_found(client: TestClient) -> None:
    missing_upload = client.get("/portfolios/uploads/does-not-exist")
    assert missing_upload.status_code == 404
    missing_portfolio = client.get("/portfolios/does-not-exist")
    assert missing_portfolio.status_code == 404
    missing_summary = client.get("/portfolios/does-not-exist/summary")
    assert missing_summary.status_code == 404
    missing_holdings = client.get("/portfolios/does-not-exist/holdings")
    assert missing_holdings.status_code == 404
    missing_confirm = client.post("/portfolios/uploads/does-not-exist/confirm")
    assert missing_confirm.status_code == 404
