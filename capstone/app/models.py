from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class AuthBase(DeclarativeBase):
    pass


class FinanceBase(DeclarativeBase):
    pass


class StockBase(DeclarativeBase):
    pass


class User(AuthBase):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, nullable=False, default="analyst")
    portfolio_ids = Column(Text, nullable=False, default="[]")
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)


class ChatSession(AuthBase):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)


class Turn(AuthBase):
    __tablename__ = "turns"

    turn_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    user_id = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    profile_id = Column(String, nullable=False, default="default", index=True)
    outcome = Column(String, nullable=False)
    category = Column(String)
    answer = Column(Text)
    envelope_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Profile(AuthBase):
    __tablename__ = "profiles"

    profile_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProfileGuideline(AuthBase):
    __tablename__ = "profile_guidelines"
    __table_args__ = (UniqueConstraint("user_id", "profile_id", "use_case"),)

    guideline_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    profile_id = Column(String, nullable=False, index=True)
    use_case = Column(String, nullable=False)
    guideline_text = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


class SavedScreen(AuthBase):
    __tablename__ = "saved_screens"

    screen_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    profile_id = Column(String, nullable=False, default="default", index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    definition = Column(Text, nullable=False)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class EscalationRecord(AuthBase):
    __tablename__ = "escalations"

    escalation_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    session_id = Column(String)
    trace_id = Column(String, nullable=False)
    triggers = Column(Text, nullable=False)
    reason = Column(Text)
    reviewer = Column(String)
    envelope_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class TraceRecord(AuthBase):
    __tablename__ = "traces"

    trace_id = Column(String, primary_key=True)
    user_id = Column(String)
    session_id = Column(String)
    query = Column(Text)
    category = Column(String)
    outcome = Column(String)
    spans_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(AuthBase):
    __tablename__ = "audit_log"

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String)
    query_id = Column(String)
    role = Column(String)
    params_json = Column(Text)
    row_count = Column(Integer)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class IdempotencyKey(AuthBase):
    __tablename__ = "idempotency_keys"

    key = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    envelope_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Portfolio(FinanceBase):
    __tablename__ = "portfolios"

    portfolio_id = Column(Integer, primary_key=True)
    portfolio_name = Column(String(150), nullable=False)
    portfolio_manager = Column(String(150))
    risk_category = Column(String(50))
    total_value = Column(Numeric)
    benchmark_index = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class Holding(FinanceBase):
    __tablename__ = "portfolio_holdings"

    holding_id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.portfolio_id"))
    asset_name = Column(String(150))
    asset_type = Column(String(100))
    sector = Column(String(100))
    allocation_percentage = Column(Float)
    market_value = Column(Numeric)
    buy_price = Column(Numeric)
    buy_date = Column(Date)
    last_updated = Column(Date)


class RiskLog(FinanceBase):
    __tablename__ = "asset_risk_logs"

    risk_id = Column(Integer, primary_key=True)
    asset_name = Column(String(150))
    risk_type = Column(String(100))
    risk_score = Column(Integer)
    risk_level = Column(String(50))
    risk_description = Column(Text)
    assessment_date = Column(Date)
    escalation_flag = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketIndicator(FinanceBase):
    __tablename__ = "market_indicators"

    indicator_id = Column(Integer, primary_key=True)
    indicator_name = Column(String(150))
    region = Column(String(100))
    indicator_value = Column(Float)
    measurement_date = Column(Date)
    trend_direction = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class Decision(FinanceBase):
    __tablename__ = "investment_decisions"

    decision_id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.portfolio_id"))
    asset_name = Column(String(150))
    decision_type = Column(String(50))
    decision_reason = Column(Text)
    risk_assessment_reference = Column(Integer, ForeignKey("asset_risk_logs.risk_id"))
    decision_date = Column(Date)
    approval_status = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class PolicyChunk(FinanceBase):
    __tablename__ = "policy_chunks"

    chunk_id = Column(String, primary_key=True)
    doc_id = Column(String, nullable=False)
    doc_title = Column(String, nullable=False)
    doc_category = Column(String)
    section = Column(String)
    page = Column(Integer)
    chunk_text = Column(Text, nullable=False)
    token_count = Column(Integer)
    embedding = Column(Text)


class UserDocument(FinanceBase):
    __tablename__ = "user_documents"

    doc_id = Column(String, primary_key=True)
    owner_id = Column(String, nullable=False, index=True)
    doc_title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    category = Column(String, nullable=False)
    role = Column(String, nullable=False)
    use_case = Column(String, nullable=False, default="all")
    profile_id = Column(String, nullable=False, default="default", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StockDocument(StockBase):
    __tablename__ = "stock_documents"

    doc_id = Column(String, primary_key=True)
    owner_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    doc_title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    kind = Column(String, nullable=False, default="ar")
    body = Column(Text)
    profile_id = Column(String, nullable=False, default="default", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StockChunk(StockBase):
    __tablename__ = "stock_chunks"

    chunk_id = Column(String, primary_key=True)
    doc_id = Column(String, nullable=False, index=True)
    doc_title = Column(String, nullable=False)
    doc_category = Column(String)
    section = Column(String)
    page = Column(Integer)
    chunk_text = Column(Text, nullable=False)
    token_count = Column(Integer)
    embedding = Column(Text)


class EquityUniverse(FinanceBase):
    __tablename__ = "equity_universe"

    symbol = Column(String, primary_key=True)
    company_name = Column(String, nullable=False)
    sector = Column(String)
    industry = Column(String)
    exchange = Column(String)
    market_cap_cr = Column(Numeric)
    is_active = Column(Boolean, default=True)


class EquityFundamental(FinanceBase):
    __tablename__ = "equity_fundamentals"
    __table_args__ = (UniqueConstraint("symbol", "period_end", "period_type"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, ForeignKey("equity_universe.symbol"))
    period_end = Column(Date, nullable=False)
    period_type = Column(String, nullable=False)
    pe = Column(Numeric)
    pb = Column(Numeric)
    roe = Column(Numeric)
    roce = Column(Numeric)
    debt_to_equity = Column(Numeric)
    current_ratio = Column(Numeric)
    sales_growth_3y = Column(Numeric)
    profit_growth_3y = Column(Numeric)
    dividend_yield = Column(Numeric)
    promoter_holding = Column(Numeric)
