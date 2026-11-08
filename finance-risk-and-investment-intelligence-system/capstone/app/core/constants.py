from __future__ import annotations

from typing import Dict, Tuple

from app.core.config import get_settings

DISCLAIMER = (
    "Based on synthetic/educational data for demonstration purposes. "
    "This is not investment advice. All outputs require review by a qualified human analyst."
)

ROLES = ("analyst", "risk_manager", "compliance", "admin")
QUERY_CATEGORIES = ("C1_RAG", "C2_SQL", "C3_HYBRID", "C4_HIGH_RISK", "C5_ESCALATION")
OUTCOMES = ("answered", "refused", "escalated", "insufficient_evidence")

CATEGORY_LABELS = {
    "C1_RAG": "Investment Policy Interpretation",
    "C2_SQL": "Portfolio & Risk Data Lookup",
    "C3_HYBRID": "Hybrid Risk Evaluation",
    "C4_HIGH_RISK": "High-Risk Financial Decisions",
    "C5_ESCALATION": "Escalation / Human Handoff",
}

CATEGORY_PATHS = {
    "C1_RAG": ["retrieval", "synthesis"],
    "C2_SQL": ["portfolio_eval", "synthesis"],
    "C3_HYBRID": ["retrieval", "portfolio_eval", "risk", "synthesis"],
    "C4_HIGH_RISK": ["retrieval", "portfolio_eval", "market_data", "risk", "synthesis"],
    "C5_ESCALATION": ["escalation"],
}

TRIGGER_CATALOG = {
    "E1": ("Override / bypass intent", "The request instructs the system to bypass a risk control."),
    "E2": ("Flagged asset in scope", "An asset in scope has escalation_flag = TRUE."),
    "E3": ("Extreme or stale risk score", "A risk score exceeds the escalation threshold or a High assessment is stale."),
    "E4": ("Conflicting signals", "Policy evidence conflicts with observed portfolio or risk data."),
    "E5": ("Insufficient evidence", "Required evidence was missing or below the retrieval floor."),
    "E6": ("Policy / regulatory limit breach", "An observed value exceeds a stated policy limit."),
    "E7": ("Unapproved decision", "An in-scope decision is Pending, Under Review, or Rejected."),
    "E8": ("Low confidence", "Synthesis confidence is below the escalation floor on a high-risk path."),
}

REVIEWERS = {
    "E1": "Compliance Officer",
    "E2": "Risk Committee",
    "E3": "Risk Committee",
    "E4": "Risk Manager",
    "E5": "Investment Analyst",
    "E6": "Compliance Officer + Risk Committee",
    "E7": "Portfolio Manager + Compliance Officer",
    "E8": "Investment Analyst",
}

POLICY_DOCS = [
    {
        "doc_id": "01_Investment_Strategy_Portfolio_Allocation_Guide",
        "doc_title": "Investment Strategy & Portfolio Allocation Guide",
        "filename": "01_Investment_Strategy_Portfolio_Allocation_Guide.pdf",
        "category": "strategy",
        "role": "strategy",
        "use_case": "strategy",
        "origin": "system",
    },
    {
        "doc_id": "02_Risk_Management_Exposure_Policy",
        "doc_title": "Risk Management & Exposure Policy",
        "filename": "02_Risk_Management_Exposure_Policy.pdf",
        "category": "risk",
        "role": "policy",
        "use_case": "risk",
        "origin": "system",
    },
    {
        "doc_id": "03_Regulatory_Compliance_Financial_Governance_Policy",
        "doc_title": "Regulatory Compliance & Financial Governance Policy",
        "filename": "03_Regulatory_Compliance_Financial_Governance_Policy.pdf",
        "category": "regulatory",
        "role": "policy",
        "use_case": "regulatory",
        "origin": "system",
    },
    {
        "doc_id": "04_Market_Analysis_Investment_Research_Guide",
        "doc_title": "Market Analysis & Investment Research Guide",
        "filename": "04_Market_Analysis_Investment_Research_Guide.pdf",
        "category": "market",
        "role": "policy",
        "use_case": "research",
        "origin": "system",
    },
    {
        "doc_id": "05_Portfolio_Monitoring_Performance_Evaluation_Guide",
        "doc_title": "Portfolio Monitoring & Performance Evaluation Guide",
        "filename": "05_Portfolio_Monitoring_Performance_Evaluation_Guide.pdf",
        "category": "monitoring",
        "role": "policy",
        "use_case": "evaluation",
        "origin": "system",
    },
    {
        "doc_id": "06_Basel_III_Risk_Management_Summary",
        "doc_title": "Basel III Risk Management Summary",
        "filename": "06_Basel_III_Risk_Management_Summary.pdf",
        "category": "framework",
        "role": "policy",
        "use_case": "framework",
        "origin": "system",
    },
    {
        "doc_id": "07_Investment_Risk_Assessment_Framework",
        "doc_title": "Investment Risk Assessment Framework",
        "filename": "07_Investment_Risk_Assessment_Framework.pdf",
        "category": "framework",
        "role": "matrix",
        "use_case": "matrix",
        "origin": "system",
    },
]
POLICY_DOCS_BY_ID = {doc["doc_id"]: doc for doc in POLICY_DOCS}
HOUSE_TYPES = tuple(doc["use_case"] for doc in POLICY_DOCS)
HOUSE_LABELS = {
    "strategy": "01 Strategy / allocation",
    "risk": "02 Risk / exposure",
    "regulatory": "03 Regulatory / compliance",
    "research": "04 Research / analysis",
    "evaluation": "05 Performance evaluation",
    "framework": "06 Basel / framework",
    "matrix": "07 Risk assessment matrix",
}
STOCK_KINDS = ("ar", "concall", "ppt")
NOTE_KIND = "note"


def trigger_catalog() -> Dict[str, Tuple[str, str]]:
    settings = get_settings()
    catalog = dict(TRIGGER_CATALOG)
    catalog["E3"] = (
        "Extreme or stale risk score",
        "A risk score exceeds {} or a High assessment is older than {} days.".format(
            settings.risk_score_escalation,
            settings.stale_high_risk_days,
        ),
    )
    return catalog
