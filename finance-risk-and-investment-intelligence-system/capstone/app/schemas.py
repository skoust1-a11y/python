from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import get_settings
from app.core.constants import DISCLAIMER
from app.profiles import DEFAULT_PROFILE_ID, normalize_profile_id
from app.rag import normalize_symbol


class QueryOptions(BaseModel):
    max_results: int = Field(default_factory=lambda: get_settings().retrieval_top_k, ge=1)
    include_evidence: bool = False
    explain_routing: bool = True
    evidence_mode: Literal["corpus", "current"] = "corpus"
    symbol: Optional[str] = None
    profile_id: str = DEFAULT_PROFILE_ID
    replace_note: bool = False

    @field_validator("max_results")
    @classmethod
    def _cap_max_results(cls, value: int) -> int:
        cap = get_settings().retrieval_top_k_max
        if value > cap:
            raise ValueError("max_results must be <= {}".format(cap))
        return value

    @field_validator("symbol")
    @classmethod
    def _norm_symbol(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return None
        symbol = normalize_symbol(value)
        if symbol is None:
            raise ValueError("symbol must be a ticker like SYNTECH")
        return symbol

    @field_validator("profile_id")
    @classmethod
    def _norm_profile(cls, value: Optional[str]) -> str:
        return normalize_profile_id(value)


class QueryRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "query": "Are any assets exceeding the allowed risk thresholds?",
                    "session_id": "sess_9f3a0001",
                    "options": {
                        "max_results": 5,
                        "include_evidence": False,
                        "explain_routing": True,
                    },
                }
            ]
        },
    )

    query: str = Field(..., min_length=3, max_length=2000)
    session_id: Optional[str] = Field(None, pattern=r"^sess_[a-zA-Z0-9]{8,}$")
    options: QueryOptions = Field(default_factory=QueryOptions)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("query must be at least 3 characters after strip")
        return cleaned


class SessionRename(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be empty")
        return cleaned


class DocCitation(BaseModel):
    type: Literal["doc"] = "doc"
    doc_id: str
    doc_title: str
    section: str
    page: int
    chunk_id: str
    score: float
    doc_category: Optional[str] = None
    filename: Optional[str] = None
    origin: Literal["system", "user"] = "system"
    role: Optional[Literal["strategy", "matrix", "policy"]] = None
    excerpt: Optional[str] = None


class SqlCitation(BaseModel):
    type: Literal["sql"] = "sql"
    query_id: str
    tables: List[str]
    params: Dict[str, Any]
    row_count: int
    executed_at: datetime


class QuoteCitation(BaseModel):
    type: Literal["quote"] = "quote"
    symbol: str
    price: float
    as_of: datetime
    provider_id: str
    stale: bool = False


class NewsCitation(BaseModel):
    type: Literal["news"] = "news"
    headline: str
    source: str
    url: str
    published_at: datetime
    provider_id: str


Citation = Annotated[
    Union[DocCitation, SqlCitation, QuoteCitation, NewsCitation],
    Field(discriminator="type"),
]


class RoutingInfo(BaseModel):
    category: str
    category_label: str
    path: List[str]
    agents_used: List[str]
    confidence: float
    rationale: Optional[str] = None


class BreachedThreshold(BaseModel):
    name: str
    policy_value: float
    observed_value: float
    unit: str
    source_chunk_id: Optional[str] = None
    source_query_id: Optional[str] = None


class FlaggedAsset(BaseModel):
    asset_name: str
    risk_id: int
    risk_score: int
    escalation_flag: bool


class RiskBlock(BaseModel):
    level: Optional[str] = None
    rationale: Optional[str] = None
    any_escalation_flag: bool = False
    breached_thresholds: List[BreachedThreshold] = Field(default_factory=list)
    flagged_assets: List[FlaggedAsset] = Field(default_factory=list)


class TriggerDetail(BaseModel):
    id: str
    name: str
    description: str


class EscalationBlock(BaseModel):
    required: bool
    triggers: List[str] = Field(default_factory=list)
    trigger_details: List[TriggerDetail] = Field(default_factory=list)
    reason: Optional[str] = None
    recommended_reviewer: Optional[str] = None
    escalation_id: Optional[str] = None


class ResultTable(BaseModel):
    title: str
    columns: List[str]
    rows: List[List[str]]
    total_rows: int = 0


class QueryResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "trace_id": "trc_7c21ab12",
                    "session_id": "sess_9f3a0001",
                    "outcome": "answered",
                    "answer": "Emerging-market exposure is capped at 15% of the book.",
                    "data_tables": [],
                    "citations": [
                        {
                            "type": "doc",
                            "doc_id": "02_Risk_Management_Exposure_Policy",
                            "doc_title": "Risk Management & Exposure Policy",
                            "section": "Exposure Limits",
                            "page": 14,
                            "chunk_id": "chunk_02_014_3",
                            "score": 0.87,
                            "origin": "system",
                        }
                    ],
                    "routing": {
                        "category": "C3_HYBRID",
                        "category_label": "Hybrid Risk Evaluation",
                        "path": ["retrieval", "portfolio_eval", "risk", "synthesis"],
                        "agents_used": ["router", "retrieval", "portfolio_eval", "risk", "synthesis"],
                        "confidence": 0.92,
                        "rationale": "Policy thresholds compared against observed risk scores.",
                    },
                    "risk": {
                        "level": "High",
                        "rationale": "Two holdings sit above the escalation threshold.",
                        "any_escalation_flag": True,
                        "breached_thresholds": [],
                        "flagged_assets": [],
                    },
                    "escalation": {
                        "required": False,
                        "triggers": [],
                        "trigger_details": [],
                    },
                    "confidence": 0.91,
                    "evidence_summary": {"doc": 1, "sql": 1},
                    "gaps": [],
                    "disclaimer": DISCLAIMER,
                    "latency_ms": 840,
                    "token_usage": {"prompt": 120, "completion": 80},
                    "cost_usd": 0.002,
                    "model_info": {"router": "deterministic", "synthesis": "local"},
                    "evidence_mode_used": "corpus",
                    "saved_note": False,
                }
            ]
        }
    )

    trace_id: str
    session_id: str
    outcome: Literal["answered", "refused", "escalated", "insufficient_evidence"]
    answer: str
    data_tables: List[ResultTable] = Field(default_factory=list)
    citations: List[Citation]
    routing: RoutingInfo
    risk: RiskBlock
    escalation: EscalationBlock
    confidence: float
    evidence_summary: Dict[str, int]
    gaps: List[str] = Field(default_factory=list)
    disclaimer: str
    latency_ms: int
    token_usage: Dict[str, int]
    cost_usd: float
    model_info: Dict[str, str]
    evidence_mode_used: Literal["corpus", "current"]
    evidence: Optional[Dict[str, Any]] = None
    saved_note: bool = False

    @model_validator(mode="after")
    def invariants(self) -> "QueryResponse":
        if not self.disclaimer:
            raise ValueError("disclaimer is required")
        if self.outcome == "answered" and len(self.citations) < 1:
            raise ValueError("answered outcome requires at least one citation")
        if self.outcome == "escalated":
            if not self.escalation.required or not self.escalation.recommended_reviewer:
                raise ValueError("escalated outcome requires reviewer and required=true")
        if self.routing.category == "C3_HYBRID" and self.outcome == "answered":
            types = {c.type for c in self.citations}
            has_corpus = "doc" in types and "sql" in types
            has_current = self.evidence_mode_used == "current" and (("quote" in types) or ("news" in types))
            if not has_corpus and not has_current:
                raise ValueError("C3 answered responses need both doc and sql citations")
        return self


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=150)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


class UserOut(BaseModel):
    user_id: str
    email: str
    role: str
    portfolio_ids: List[int] = Field(default_factory=list)
    full_name: Optional[str] = None
    status: str = "active"
    features: Dict[str, bool] = Field(default_factory=dict)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class SignupResponse(BaseModel):
    user_id: str
    email: str
    role: str


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class GuidelinePut(BaseModel):
    guideline_text: str = Field(..., max_length=20000)


class AdminUserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Optional[str] = None
    portfolio_ids: Optional[List[int]] = None
    status: Optional[str] = None


class ScreenFilter(BaseModel):
    field: str
    op: str
    value: Any = None


class ScreenSort(BaseModel):
    field: str
    dir: Literal["asc", "desc"] = "desc"


class ScreenPeriod(BaseModel):
    type: Literal["FY", "Q"] = "FY"
    as_of: str = "latest"


class ScreenDefinition(BaseModel):
    version: int = 1
    logic: Literal["and", "or"] = "and"
    filters: List[ScreenFilter] = Field(default_factory=list)
    sort: List[ScreenSort] = Field(default_factory=list)
    limit: int = Field(50, ge=1, le=200)
    period: ScreenPeriod = Field(default_factory=ScreenPeriod)


class ScreenRunRequest(BaseModel):
    definition: ScreenDefinition


class ScreenSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    definition: ScreenDefinition
    is_public: bool = False


class ScreenNlRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    auto_run: bool = True


DEFAULT_DISCLAIMER = DISCLAIMER
