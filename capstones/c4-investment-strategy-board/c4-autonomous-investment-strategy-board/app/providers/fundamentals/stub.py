"""Placeholder fundamentals adapter. Does not invent financial metrics."""

from __future__ import annotations

from app.config.settings import Settings
from app.exceptions import ProviderNotImplementedError
from app.models.fundamentals import (
    CompanyProfile,
    FinancialMetrics,
    FinancialStatement,
    ReportingPeriod,
    StatementType,
    ValuationMetrics,
)
from app.providers.contracts import FundamentalDataProvider


class StubFundamentalDataProvider(FundamentalDataProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "stub"

    def get_company_profile(self, instrument: str) -> CompanyProfile:
        raise self._unavailable("Company profiles")

    def get_financial_statements(
        self,
        instrument: str,
        *,
        statement_type: StatementType = "income",
        period: ReportingPeriod = "annual",
    ) -> list[FinancialStatement]:
        raise self._unavailable("Financial statements")

    def get_key_metrics(self, instrument: str) -> FinancialMetrics:
        raise self._unavailable("Key financial metrics")

    def get_valuation_metrics(self, instrument: str) -> ValuationMetrics:
        raise self._unavailable("Valuation metrics")

    def _unavailable(self, artifact: str) -> ProviderNotImplementedError:
        return ProviderNotImplementedError(
            "Fundamental-data adapter is not implemented yet. "
            f"{artifact} must come from an external provider, not from application stubs or LLM knowledge."
        )
