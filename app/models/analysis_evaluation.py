"""Structured analysis evaluation models."""



from __future__ import annotations



from typing import Literal



from pydantic import BaseModel, Field



ClaimStatus = Literal["supported", "partially_supported", "unsupported"]

CoverageLevel = Literal["high", "medium", "low"]





class ClaimEvaluation(BaseModel):

    claim: str

    status: ClaimStatus

    supporting_sources: list[str] = Field(default_factory=list)

    notes: str | None = None

    requires_inference: bool = False

    calculation: bool = False



    @property

    def evidence(self) -> list[str]:

        return self.supporting_sources



    @property

    def reason(self) -> str | None:

        return self.notes





class RetrievalAssessment(BaseModel):

    coverage: CoverageLevel = "medium"

    missing_topics: list[str] = Field(default_factory=list)

    irrelevant_chunks: list[str] = Field(default_factory=list)





class AnalysisEvaluation(BaseModel):

    """Structured output from Analysis mode claim evaluation."""



    claims: list[ClaimEvaluation] = Field(default_factory=list)

    retrieval_assessment: RetrievalAssessment = Field(default_factory=RetrievalAssessment)

    missing_evidence: list[str] = Field(default_factory=list)

    missing_information: list[str] = Field(default_factory=list)

    assumptions: list[str] = Field(default_factory=list)

    inferences: list[str] = Field(default_factory=list)

    calculations: list[str] = Field(default_factory=list)

    ambiguities: list[str] = Field(default_factory=list)

    hallucination_detected: bool = False

    summary: str | None = None

    faithfulness: float = Field(default=0.0, ge=0.0, le=1.0)

    relevance: float = Field(default=0.0, ge=0.0, le=1.0)

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    metrics_explanation: str | None = None


