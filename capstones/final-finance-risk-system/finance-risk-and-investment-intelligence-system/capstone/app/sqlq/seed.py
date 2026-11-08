"""Create and seed the two local SQLite databases (auth + finance)."""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, timedelta
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core import db as dbmod
from app.core.db import drop_schema, init_schema
from app.core.security import hash_password, verify_password
from app.models import (
    Decision,
    EquityFundamental,
    EquityUniverse,
    Holding,
    MarketIndicator,
    PolicyChunk,
    Portfolio,
    RiskLog,
    User,
)

RNG = random.Random(42)

NUM_PORTFOLIOS = 20
NUM_HOLDINGS = 120
NUM_RISK_LOGS = 150
NUM_MARKET_INDICATORS = 80
NUM_INVESTMENT_DECISIONS = 100

MANAGERS = [
    "Alice Morgan",
    "David Chen",
    "Ravi Patel",
    "Sophia Martinez",
    "Daniel Kim",
    "Emma Wilson",
]
RISK_CATEGORIES = ["Low", "Medium", "High"]
BENCHMARKS = ["S&P 500", "NASDAQ 100", "MSCI World", "FTSE 100", "MSCI Emerging Markets"]
ASSETS = [
    "Apple Inc",
    "Tesla",
    "Microsoft",
    "Amazon",
    "Google",
    "Nvidia",
    "JPMorgan",
    "Gold ETF",
    "Oil Futures",
    "US Treasury Bonds",
    "Emerging Market ETF",
    "Corporate Bond Fund",
]
ASSET_TYPES = ["Equity", "ETF", "Bond", "Commodity"]
SECTORS = ["Technology", "Finance", "Energy", "Healthcare", "Consumer"]
RISK_TYPES = [
    "Market Volatility",
    "Liquidity Risk",
    "Regulatory Risk",
    "Credit Risk",
    "Geopolitical Risk",
    "Market Risk",
]
DECISION_TYPES = ["BUY", "SELL", "HOLD"]
REGIONS = ["US", "Europe", "Asia", "Global"]
INDICATORS = [
    "Inflation Rate",
    "Interest Rate",
    "GDP Growth",
    "Unemployment Rate",
    "Consumer Confidence Index",
]
TRENDS = ["Increasing", "Decreasing", "Stable", "Rising"]
APPROVALS = ["Approved", "Pending", "Rejected", "Under Review"]

LOCAL_USERS = [
    ("u_admin", "admin@local", "admin", "ALL", "Local Admin"),
    ("u_risk", "risk@local", "risk_manager", "ALL", "Local Risk Manager"),
    ("u_comp", "compliance@local", "compliance", "ALL", "Local Compliance"),
    ("u_analyst", "analyst@local", "analyst", "[1, 2]", "Local Analyst"),
]
LOCAL_PASSWORD = get_settings().seed_password

POLICY_CHUNKS = [
    (
        "chunk_01_div_1",
        "01_Investment_Strategy_Portfolio_Allocation_Guide",
        "Investment Strategy & Portfolio Allocation Guide",
        "strategy",
        "Diversification",
        4,
        "High-risk portfolios should diversify across at least five sectors. "
        "No single sector may exceed 25% of portfolio market value without documented review.",
    ),
    (
        "chunk_01_em_1",
        "01_Investment_Strategy_Portfolio_Allocation_Guide",
        "Investment Strategy & Portfolio Allocation Guide",
        "strategy",
        "Emerging markets",
        8,
        "Emerging-market equity exposure is optional for growth books and should stay "
        "inside the risk-policy cap. Rebalance when drift exceeds 2 percentage points.",
    ),
    (
        "chunk_02_em_cap",
        "02_Risk_Management_Exposure_Policy",
        "Risk Management & Exposure Policy",
        "risk",
        "Exposure Limits",
        14,
        "Exposure to emerging market assets is capped at 15% of total portfolio value. "
        "A breach requires risk-committee notification the same business day.",
    ),
    (
        "chunk_02_liq",
        "02_Risk_Management_Exposure_Policy",
        "Risk Management & Exposure Policy",
        "risk",
        "Liquidity Risk",
        9,
        "Liquidity risk is the risk that a position cannot be exited within five trading "
        "days without moving the price more than 2%. Illiquid names need a dedicated limit.",
    ),
    (
        "chunk_03_esc",
        "03_Regulatory_Compliance_Financial_Governance_Policy",
        "Regulatory Compliance & Financial Governance Policy",
        "regulatory",
        "Escalation procedures",
        11,
        "A regulatory breach is escalated to the Compliance Officer and recorded in the "
        "audit log. The system must not approve or waive a control on its own.",
    ),
    (
        "chunk_04_macro",
        "04_Market_Analysis_Investment_Research_Guide",
        "Market Analysis & Investment Research Guide",
        "market",
        "Macro indicators",
        6,
        "Inflation, policy rates, and GDP growth are interpreted together. A rising "
        "inflation print with rising rates is a tightening signal, not a buy recommendation.",
    ),
    (
        "chunk_05_bench",
        "05_Portfolio_Monitoring_Performance_Evaluation_Guide",
        "Portfolio Monitoring & Performance Evaluation Guide",
        "monitoring",
        "Benchmark comparison",
        5,
        "Compare excess return and tracking error versus the assigned benchmark index. "
        "Document the method (arithmetic excess, not a forecast).",
    ),
    (
        "chunk_06_lcr",
        "06_Basel_III_Risk_Management_Summary",
        "Basel III Risk Management Summary",
        "framework",
        "Liquidity coverage",
        7,
        "The Liquidity Coverage Ratio requires high-quality liquid assets sufficient to "
        "cover net cash outflows over a 30-day stress horizon.",
    ),
    (
        "chunk_07_tiers",
        "07_Investment_Risk_Assessment_Framework",
        "Investment Risk Assessment Framework",
        "framework",
        "Risk classification tiers",
        3,
        "Risk scores run 0-100. Low is below 30, Medium is 30-69, High is 70 or above. "
        "escalation_flag is TRUE when the score is above 80. High-risk approvals need a current assessment.",
    ),
]

EQUITIES = [
    ("SYNTECH", "Syntech Systems", "Technology", "Software", "NSE", 12000),
    ("HELIXPH", "Helix Pharma", "Healthcare", "Pharma", "NSE", 8500),
    ("RIVFIN", "River Finance", "Finance", "Banks", "NSE", 22000),
    ("OILGRID", "Oilgrid Energy", "Energy", "Oil & Gas", "BSE", 15000),
    ("CONSMRT", "Consumer Mart", "Consumer", "Retail", "NSE", 6400),
    ("NANOSEMI", "Nanosemi", "Technology", "Semiconductors", "NYSE", 48000),
    ("GREENBND", "Green Bond Trust", "Finance", "Bonds", "NSE", 3100),
    ("MEDCARE", "Medcare Hospitals", "Healthcare", "Hospitals", "BSE", 4200),
]


def _rand_date() -> date:
    start = datetime(2024, 1, 1)
    end = datetime(2025, 3, 1)
    return (start + timedelta(days=RNG.randint(0, (end - start).days))).date()


def _risk_level(score: int) -> str:
    settings = get_settings()
    if score < settings.risk_score_medium:
        return "Low"
    if score < settings.risk_score_high:
        return "Medium"
    return "High"


def seed_users(session: Session) -> int:
    if session.query(User).count():
        emails = [row[1] for row in LOCAL_USERS]
        for user in session.query(User).filter(User.email.in_(emails)):
            if not verify_password(LOCAL_PASSWORD, user.password_hash):
                user.password_hash = hash_password(LOCAL_PASSWORD)
        session.commit()
        return 0
    password_hash = hash_password(LOCAL_PASSWORD)
    for user_id, email, role, portfolio_ids, full_name in LOCAL_USERS:
        session.add(
            User(
                user_id=user_id,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=role,
                portfolio_ids=portfolio_ids,
                status="active",
            )
        )
    session.commit()
    return len(LOCAL_USERS)


def seed_finance_core(session: Session) -> None:
    if session.query(Portfolio).count():
        return

    official_portfolios = [
        (1, "Global Growth Fund", "Arjun Mehta", "High", 250000000, "MSCI World"),
        (2, "Balanced Income Fund", "Priya Nair", "Medium", 180000000, "S&P 500"),
        (3, "Emerging Markets Opportunity", "Rahul Kapoor", "High", 120000000, "MSCI Emerging Markets"),
        (4, "Conservative Bond Strategy", "Neha Iyer", "Low", 90000000, "Bloomberg Global Aggregate"),
    ]
    for row in official_portfolios:
        session.add(
            Portfolio(
                portfolio_id=row[0],
                portfolio_name=row[1],
                portfolio_manager=row[2],
                risk_category=row[3],
                total_value=row[4],
                benchmark_index=row[5],
            )
        )
    for i in range(5, NUM_PORTFOLIOS + 1):
        session.add(
            Portfolio(
                portfolio_id=i,
                portfolio_name="Global Growth Portfolio {}".format(i),
                portfolio_manager=RNG.choice(MANAGERS),
                risk_category=RNG.choice(RISK_CATEGORIES),
                total_value=RNG.randint(5_000_000, 50_000_000),
                benchmark_index=RNG.choice(BENCHMARKS),
            )
        )
    session.flush()

    official_holdings = [
        (1, 1, "Apple Inc", "Equity", "Technology", 8.5, 21250000, date(2025, 2, 1)),
        (2, 1, "Microsoft Corp", "Equity", "Technology", 7.2, 18000000, date(2025, 2, 1)),
        (3, 2, "US Treasury Bonds", "Bond", "Government", 15.0, 27000000, date(2025, 1, 15)),
        (4, 3, "Reliance Industries", "Equity", "Energy", 6.3, 7560000, date(2025, 1, 20)),
        (5, 1, "Nvidia", "Equity", "Technology", 12.0, 30000000, date(2025, 2, 1)),
        (6, 3, "Emerging Market ETF", "ETF", "Finance", 18.4, 22080000, date(2025, 1, 22)),
    ]
    for row in official_holdings:
        session.add(
            Holding(
                holding_id=row[0],
                portfolio_id=row[1],
                asset_name=row[2],
                asset_type=row[3],
                sector=row[4],
                allocation_percentage=row[5],
                market_value=row[6],
                last_updated=row[7],
            )
        )
    for i in range(len(official_holdings) + 1, NUM_HOLDINGS + 1):
        session.add(
            Holding(
                holding_id=i,
                portfolio_id=RNG.randint(1, NUM_PORTFOLIOS),
                asset_name=RNG.choice(ASSETS),
                asset_type=RNG.choice(ASSET_TYPES),
                sector=RNG.choice(SECTORS),
                allocation_percentage=round(RNG.uniform(1, 25), 2),
                market_value=RNG.randint(50_000, 5_000_000),
                last_updated=_rand_date(),
            )
        )
    session.flush()

    official_risk = [
        (1, "Apple Inc", "Market Risk", 45, "Medium", "Exposure to global tech sector volatility", date(2025, 1, 10), False),
        (2, "Emerging Market ETF", "Market Risk", 91, "High", "High volatility due to geopolitical uncertainty", date(2025, 1, 15), True),
        (3, "Corporate Bond Fund", "Credit Risk", 62, "Medium", "Moderate credit exposure to BBB rated issuers", date(2025, 1, 12), False),
        (4, "Tesla", "Market Volatility", 84, "High", "Score above the escalation threshold", date(2024, 6, 1), True),
    ]
    for row in official_risk:
        session.add(
            RiskLog(
                risk_id=row[0],
                asset_name=row[1],
                risk_type=row[2],
                risk_score=row[3],
                risk_level=row[4],
                risk_description=row[5],
                assessment_date=row[6],
                escalation_flag=row[7],
            )
        )
    for i in range(len(official_risk) + 1, NUM_RISK_LOGS + 1):
        score = RNG.randint(0, 100)
        session.add(
            RiskLog(
                risk_id=i,
                asset_name=RNG.choice(ASSETS),
                risk_type=RNG.choice(RISK_TYPES),
                risk_score=score,
                risk_level=_risk_level(score),
                risk_description="Synthetic assessment for local seed.",
                assessment_date=_rand_date(),
                escalation_flag=score > get_settings().risk_score_escalation,
            )
        )
    session.flush()

    official_mkt = [
        (1, "Inflation Rate", "US", 3.2, date(2025, 1, 1), "Rising"),
        (2, "Interest Rate", "EU", 2.75, date(2025, 1, 5), "Stable"),
        (3, "GDP Growth", "APAC", 4.8, date(2025, 1, 10), "Increasing"),
    ]
    for row in official_mkt:
        session.add(
            MarketIndicator(
                indicator_id=row[0],
                indicator_name=row[1],
                region=row[2],
                indicator_value=row[3],
                measurement_date=row[4],
                trend_direction=row[5],
            )
        )
    for i in range(len(official_mkt) + 1, NUM_MARKET_INDICATORS + 1):
        session.add(
            MarketIndicator(
                indicator_id=i,
                indicator_name=RNG.choice(INDICATORS),
                region=RNG.choice(REGIONS),
                indicator_value=round(RNG.uniform(1.0, 10.0), 2),
                measurement_date=_rand_date(),
                trend_direction=RNG.choice(TRENDS),
            )
        )
    session.flush()

    official_decisions = [
        (1, 1, "Apple Inc", "Buy", "Strong earnings growth and market leadership", 1, date(2025, 1, 20), "Approved"),
        (2, 3, "Emerging Market ETF", "Reduce Exposure", "High market volatility risk detected", 2, date(2025, 1, 22), "Under Review"),
        (3, 2, "Corporate Bond Fund", "Hold", "Stable credit outlook with moderate yield", 3, date(2025, 1, 18), "Approved"),
        (4, 1, "Nvidia", "BUY", "Pending committee approval", 4, date(2025, 2, 2), "Pending"),
    ]
    for row in official_decisions:
        session.add(
            Decision(
                decision_id=row[0],
                portfolio_id=row[1],
                asset_name=row[2],
                decision_type=row[3],
                decision_reason=row[4],
                risk_assessment_reference=row[5],
                decision_date=row[6],
                approval_status=row[7],
            )
        )
    for i in range(len(official_decisions) + 1, NUM_INVESTMENT_DECISIONS + 1):
        session.add(
            Decision(
                decision_id=i,
                portfolio_id=RNG.randint(1, NUM_PORTFOLIOS),
                asset_name=RNG.choice(ASSETS),
                decision_type=RNG.choice(DECISION_TYPES),
                decision_reason="Decision based on market trend and portfolio diversification strategy.",
                risk_assessment_reference=RNG.randint(1, NUM_RISK_LOGS),
                decision_date=_rand_date(),
                approval_status=RNG.choice(APPROVALS),
            )
        )
    session.commit()


def apply_golden_extensions(session: Session) -> None:
    """Pin rows the golden set depends on (12 §1.2 step 4)."""
    nvidia = session.get(Holding, 5)
    cap = get_settings().sector_allocation_cap
    if nvidia is not None and (nvidia.allocation_percentage or 0) <= cap:
        nvidia.allocation_percentage = cap + 1.5
    extra = session.get(RiskLog, 5)
    if extra is None:
        session.add(
            RiskLog(
                risk_id=5,
                asset_name="Nvidia",
                risk_type="Market Volatility",
                risk_score=88,
                risk_level="High",
                risk_description="Pinned golden-set high-score asset.",
                assessment_date=date.today() - timedelta(days=200),
                escalation_flag=True,
            )
        )
    tesla = session.get(RiskLog, 4)
    if tesla is not None:
        tesla.assessment_date = date.today() - timedelta(days=200)
        tesla.risk_score = 84
        tesla.escalation_flag = True
        tesla.risk_level = "High"
    session.commit()


def seed_policy_chunks(session: Session) -> int:
    if session.query(PolicyChunk).count():
        return 0
    for row in POLICY_CHUNKS:
        session.add(
            PolicyChunk(
                chunk_id=row[0],
                doc_id=row[1],
                doc_title=row[2],
                doc_category=row[3],
                section=row[4],
                page=row[5],
                chunk_text=row[6],
                token_count=len(row[6].split()),
            )
        )
    session.commit()
    return len(POLICY_CHUNKS)


def seed_equities(session: Session) -> int:
    if session.query(EquityUniverse).count():
        return 0
    for symbol, name, sector, industry, exchange, mcap in EQUITIES:
        session.add(
            EquityUniverse(
                symbol=symbol,
                company_name=name,
                sector=sector,
                industry=industry,
                exchange=exchange,
                market_cap_cr=mcap,
                is_active=True,
            )
        )
    session.flush()
    for symbol, name, sector, industry, exchange, mcap in EQUITIES:
        session.add(
            EquityFundamental(
                symbol=symbol,
                period_end=date(2025, 3, 31),
                period_type="FY",
                pe=round(RNG.uniform(8, 35), 1),
                pb=round(RNG.uniform(1, 8), 1),
                roe=round(RNG.uniform(8, 28), 1),
                roce=round(RNG.uniform(7, 24), 1),
                debt_to_equity=round(RNG.uniform(0.1, 1.4), 2),
                current_ratio=round(RNG.uniform(0.8, 2.5), 2),
                sales_growth_3y=round(RNG.uniform(-2, 22), 1),
                profit_growth_3y=round(RNG.uniform(-4, 25), 1),
                dividend_yield=round(RNG.uniform(0, 4), 2),
                promoter_holding=round(RNG.uniform(20, 70), 1),
            )
        )
    session.commit()
    return len(EQUITIES)


def counts(auth: Session, finance: Session) -> Dict[str, int]:
    return {
        "users": auth.query(func.count(User.user_id)).scalar() or 0,
        "portfolios": finance.query(func.count(Portfolio.portfolio_id)).scalar() or 0,
        "holdings": finance.query(func.count(Holding.holding_id)).scalar() or 0,
        "risk_logs": finance.query(func.count(RiskLog.risk_id)).scalar() or 0,
        "market_indicators": finance.query(func.count(MarketIndicator.indicator_id)).scalar() or 0,
        "decisions": finance.query(func.count(Decision.decision_id)).scalar() or 0,
        "policy_chunks": finance.query(func.count(PolicyChunk.chunk_id)).scalar() or 0,
        "equities": finance.query(func.count(EquityUniverse.symbol)).scalar() or 0,
    }


def bootstrap(reset: bool = False) -> Dict[str, int]:
    if reset:
        drop_schema()
    init_schema()
    auth = dbmod.AuthSessionLocal()
    finance = dbmod.FinanceSessionLocal()
    try:
        seed_users(auth)
        seed_finance_core(finance)
        seed_policy_chunks(finance)
        seed_equities(finance)
        apply_golden_extensions(finance)
        try:
            from app.rag import reindex_from_pdfs

            n = 0 if finance.query(PolicyChunk).count() else reindex_from_pdfs()
            if n:
                print("ingested_pdf_chunks", n)
        except Exception as exc:  # noqa: BLE001
            print("pdf_ingest_skipped", str(exc))
        return counts(auth, finance)
    finally:
        auth.close()
        finance.close()


def main(argv: List[str] = None) -> None:
    parser = argparse.ArgumentParser(description="Create and seed local SQLite databases")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate local files")
    args = parser.parse_args(argv)
    summary = bootstrap(reset=args.reset)
    print(json.dumps(summary, indent=2))
    print("Local password for seeded users: {}".format(LOCAL_PASSWORD))


if __name__ == "__main__":
    main()
