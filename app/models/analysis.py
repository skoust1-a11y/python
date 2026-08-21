"""Public analysis request and response models.

These models are the HTTP contract. Graph-only fields (node names, specialist
extras, prompts, and hidden reasoning) stay off this surface.
"""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from app.models.common import DomainModel, Evidence
from app.models.types import NonEmptyText, NonNegativeFinite, Symbol, UnitInterval
from app.workflow.state import (
    AgentRunStatus,
    AnalysisType,
    ConflictRecord,
    CritiqueRecord,
    FinalRecommendation,
    FundamentalDataSnapshot,
    InvestmentHorizon,
    MarketDataSnapshot,
    NewsSnapshot,
    OptimizationResultSnapshot,
    RiskAnalysisSnapshot,
    RiskTolerance,
    WorkflowStatus,
)


class PortfolioAnalysisRequest(DomainModel):
    """User question about an imported portfolio. Symbols come from holdings."""

    question: NonEmptyText
    analysis_type: AnalysisType | None = None
    risk_tolerance: RiskTolerance | None = None
    horizon: InvestmentHorizon | None = None
    objective: str | None = None


class SpecialistResult(DomainModel):
    """Compact specialist outcome. Prompts, extras, and reasoning are omitted."""

    agent: NonEmptyText
    role: NonEmptyText
    status: AgentRunStatus
    summary: NonEmptyText
    findings: list[NonEmptyText] = Field(default_factory=list)
    confidence: UnitInterval | None = None
    error_message: str | None = None


class AnalysisExecution(DomainModel):
    """Client-facing run metadata. Graph node names are omitted."""

    status: WorkflowStatus
    requested_agents: list[NonEmptyText] = Field(default_factory=list)
    invoked_agents: list[NonEmptyText] = Field(default_factory=list)
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    duration_ms: NonNegativeFinite | None = None
    errors: list[NonEmptyText] = Field(default_factory=list)


class PortfolioAnalysisSummary(DomainModel):
    """Listing row for a stored analysis run."""

    id: str
    portfolio_id: str
    question: NonEmptyText
    analysis_type: AnalysisType | None = None
    status: WorkflowStatus
    created_at: AwareDatetime


class PortfolioAnalysisResult(DomainModel):
    """Structured analysis returned to the client after one workflow run."""

    id: str
    portfolio_id: str
    question: NonEmptyText
    analysis_type: AnalysisType | None = None
    status: WorkflowStatus
    recommendation: FinalRecommendation | None = None
    specialist_results: list[SpecialistResult] = Field(default_factory=list)
    risk_analysis: RiskAnalysisSnapshot | None = None
    optimization: OptimizationResultSnapshot | None = None
    market_data: list[MarketDataSnapshot] = Field(default_factory=list)
    fundamental_data: list[FundamentalDataSnapshot] = Field(default_factory=list)
    news: list[NewsSnapshot] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    conflicts: list[ConflictRecord] = Field(default_factory=list)
    critiques: list[CritiqueRecord] = Field(default_factory=list)
    execution: AnalysisExecution
    created_at: AwareDatetime


class StockAnalysisRequest(DomainModel):
    """User question about a selected stock. Does not use an uploaded portfolio."""

    question: NonEmptyText
    analysis_type: AnalysisType | None = "stock_analysis"
    risk_tolerance: RiskTolerance | None = None
    horizon: InvestmentHorizon | None = None
    objective: str | None = None


class StockAnalysisSummary(DomainModel):
    """Listing row for a stored single-stock analysis run."""

    id: str
    symbol: Symbol
    question: NonEmptyText
    analysis_type: AnalysisType | None = None
    status: WorkflowStatus
    created_at: AwareDatetime


class StockAnalysisResult(DomainModel):
    """Structured single-stock analysis returned after one workflow run."""

    id: str
    symbol: Symbol
    question: NonEmptyText
    analysis_type: AnalysisType | None = None
    status: WorkflowStatus
    recommendation: FinalRecommendation | None = None
    specialist_results: list[SpecialistResult] = Field(default_factory=list)
    risk_analysis: RiskAnalysisSnapshot | None = None
    optimization: OptimizationResultSnapshot | None = None
    market_data: list[MarketDataSnapshot] = Field(default_factory=list)
    fundamental_data: list[FundamentalDataSnapshot] = Field(default_factory=list)
    news: list[NewsSnapshot] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    conflicts: list[ConflictRecord] = Field(default_factory=list)
    critiques: list[CritiqueRecord] = Field(default_factory=list)
    execution: AnalysisExecution
    created_at: AwareDatetime
