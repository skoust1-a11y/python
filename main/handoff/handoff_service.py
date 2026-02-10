import os
import logging
import smtplib
import datetime
import secrets
from email.mime.text import MIMEText
from typing import Dict, Any, Optional
from llama_index.core.settings import Settings


logger = logging.getLogger(__name__)

FAITHFULNESS_THRESHOLD = 0.6
RELEVANCE_THRESHOLD = 0.5
CONFIDENCE_THRESHOLD = 40

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("APPLICATION_EMAIL")
EMAIL_TO = os.getenv("SUPPORT_EMAIL")


def generate_handoff_reference_id(now: Optional[datetime.datetime] = None) -> str:
    """Generate a unique handoff reference ID in format: HO-YYYYMMDD-HHMMSS-HEXCODE"""
    # TODO: Generate ID with current UTC time (if now is None) + 3-byte hex token
    # Format: f"HO-{timestamp}-{secrets.token_hex(3).upper()}"
    raise NotImplementedError("generate_handoff_reference_id needs to be implemented")


def evaluate_score(
    faithfulness: Optional[float],
    relevance: Optional[float],
    user_question: str,
    no_chunks: bool
) -> Dict[str, Any]:
    """Determines if the system should escalate based on evaluation scores."""
    # TODO: Check triggers in order and return {"trigger": bool, "reason": str}:
    # 1. no_chunks → "retrieval returned no context"
    # 2. faithfulness or relevance is None → "evaluation scores unavailable"
    # 3. faithfulness < 0.6 → "faithfulness below threshold"
    # 4. relevance < 0.5 → "answer relevance below threshold"
    # 5. Keywords in question (human/agent/support/escalate) → "explicit user request"
    # 6. Otherwise → {"trigger": False}
    raise NotImplementedError("evaluate_score needs to be implemented")


async def evaluate_confidence_score(answer: str) -> Dict[str, Any]:
    """Evaluate LLM confidence score (0-100) and trigger handoff if below threshold (40)."""
    # TODO: Use LLM to rate confidence
    # 1. Get Settings.llm (raise ValueError if None)
    # 2. Prompt: "Rate confidence 0–100.\nAnswer: {answer}"
    # 3. Parse score from response (extract digits, default to 50)
    # 4. Return {"trigger": bool, "reason": str, "confidence": int}
    raise NotImplementedError("evaluate_confidence_score needs to be implemented")


async def evaluate_explicit_user_request(message: str) -> Dict[str, Any]:
    """LLM-based classifier for explicit user request or frustration."""
    # TODO: Use LLM to classify if user is asking for human help
    # 1. Get Settings.llm (raise ValueError if None)
    # 2. Prompt: Ask LLM to return "YES" or "NO" if user wants human help
    # 3. Check if "YES" in response.text.upper()
    # 4. Return {"trigger": bool, "reason": str}
    raise NotImplementedError("evaluate_explicit_user_request needs to be implemented")


def send_handoff_email(context: Dict[str, Any]):
    """Send human handoff email via SMTP with full context."""
    # TODO: Implement email sending
    # 1. Check SMTP config (SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO)
    # 2. Build subject: "[HUMAN HANDOFF] Ref {reference_id} – {trigger_reason}"
    # 3. Build body with all context fields (reference_id, trace_id, timestamp, priority,
    #    trigger_reason, user_metadata, query_history, generated_answer, evaluation_scores,
    #    retrieved_chunks, conversation_flow)
    # 4. Create MIMEText message and set headers
    # 5. Send via SMTP with TLS (use try/except, log errors)
    raise NotImplementedError("send_handoff_email needs to be implemented")
