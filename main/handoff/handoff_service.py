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
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    hex_code = secrets.token_hex(3).upper()
    return f"HO-{timestamp}-{hex_code}"


def evaluate_score(
    faithfulness: Optional[float],
    relevance: Optional[float],
    user_question: str,
    no_chunks: bool
) -> Dict[str, Any]:
    """Determines if the system should escalate based on evaluation scores."""
    if no_chunks:
        return {"trigger": True, "reason": "retrieval returned no context"}
    if faithfulness is None or relevance is None:
        return {"trigger": True, "reason": "evaluation scores unavailable"}
    if faithfulness < FAITHFULNESS_THRESHOLD:
        return {"trigger": True, "reason": "faithfulness below threshold"}
    if relevance < RELEVANCE_THRESHOLD:
        return {"trigger": True, "reason": "answer relevance below threshold"}
    
    keywords = ["human", "agent", "support", "escalate"]
    if any(k in user_question.lower() for k in keywords):
        return {"trigger": True, "reason": "explicit user request"}
        
    return {"trigger": False}


async def evaluate_confidence_score(answer: str) -> Dict[str, Any]:
    """Evaluate LLM confidence score (0-100) and trigger handoff if below threshold (40)."""
    llm = Settings.llm
    if llm is None:
        raise ValueError("Settings.llm is not configured")
    
    prompt = f"Rate confidence 0–100.\nAnswer: {answer}"
    try:
        response = llm.complete(prompt)
        response_text = response.text
        
        import re
        match = re.search(r'\d+', response_text)
        if match:
            score = int(match.group())
        else:
            score = 50
    except Exception as e:
        logger.error(f"Error evaluating confidence score: {e}", exc_info=True)
        score = 50
        
    score = max(0, min(100, score))
    trigger = score < CONFIDENCE_THRESHOLD
    reason = "confidence below threshold" if trigger else ""
    
    return {
        "trigger": trigger,
        "reason": reason,
        "confidence": score
    }


async def evaluate_explicit_user_request(message: str) -> Dict[str, Any]:
    """LLM-based classifier for explicit user request or frustration."""
    llm = Settings.llm
    if llm is None:
        raise ValueError("Settings.llm is not configured")
        
    prompt = (
        "Determine if the user is explicitly asking for human help, a customer support agent, "
        "escalation, or transfer to a human. Reply with YES or NO.\n\n"
        f"User Message: {message}"
    )
    try:
        response = llm.complete(prompt)
        response_text = response.text.strip().upper()
        trigger = "YES" in response_text
    except Exception as e:
        logger.error(f"Error evaluating explicit user request: {e}", exc_info=True)
        trigger = False
        
    reason = "explicit user request" if trigger else ""
    return {
        "trigger": trigger,
        "reason": reason
    }


def send_handoff_email(context: Dict[str, Any]):
    """Send human handoff email via SMTP with full context."""
    if not all([SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        logger.warning("SMTP configuration is missing. Handoff email not sent.")
        return
        
    subject = f"[HUMAN HANDOFF] Ref {context.get('reference_id')} – {context.get('trigger_reason')}"
    
    body = f"""Human Handoff Escalation Request
==================================
Reference ID: {context.get('reference_id')}
Trace ID: {context.get('trace_id')}
Timestamp: {context.get('timestamp')}
Priority: {context.get('priority')}
Trigger Reason: {context.get('trigger_reason')}

User Metadata:
--------------
{context.get('user_metadata')}

Query History:
--------------
{context.get('query_history')}

Generated Answer:
-----------------
{context.get('generated_answer')}

Evaluation Scores:
------------------
{context.get('evaluation_scores')}

Retrieved Chunks:
-----------------
{context.get('retrieved_chunks')}

Conversation Flow:
------------------
{context.get('conversation_flow')}
"""

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Handoff email sent successfully for reference {context.get('reference_id')}")
    except Exception as e:
        logger.error(f"Failed to send handoff email: {e}", exc_info=True)

