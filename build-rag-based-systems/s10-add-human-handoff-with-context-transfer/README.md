# Product Manual RAG System - Human Handoff

## Project Context

You're building a **Product Manual RAG System**, an AI-powered system that helps users get answers to questions about product features, installation, configuration, troubleshooting, and usage instructions.

This practice focuses on **human handoff** — implementing automated escalation mechanisms that detect when the RAG system cannot provide reliable answers and seamlessly transfer conversations to human support agents. You'll learn how to evaluate answer quality, detect user frustration, and trigger handoff workflows with comprehensive context.

## Problem Statement

Build a RAG system with human handoff capabilities. The system must support document indexing, query processing, and automatic escalation when answer quality falls below thresholds or users explicitly request human assistance. You need to implement handoff detection logic, confidence scoring, and email notification workflows that provide support agents with full context.

You will complete multiple implementation tasks to build this handoff-enabled RAG system:

---

### **Task 1 — Implement Handoff Service Functions**

#### Goal

Build the core handoff service functions that evaluate answer quality, detect handoff triggers, and send notification emails.

#### Requirements

1. Implement `generate_handoff_reference_id()` to generate unique handoff reference IDs in format "HO-{YYYYMMDD-HHMMSS}-{6-char-hex-uppercase}"

2. Implement `evaluate_score()` to determine if handoff should be triggered based on faithfulness, relevance, and retrieval status

3. Implement `evaluate_confidence_score()` to evaluate LLM confidence score for generated answers using LLM-as-a-judge

4. Implement `evaluate_explicit_user_request()` to classify explicit user requests for human help using LLM-based classification

5. Implement `send_handoff_email()` to send handoff notification emails via SMTP with full context

**File**: `main/handoff/handoff_service.py`

---

### **Task 2 — Implement Query Endpoint with Handoff Logic**

#### Goal

Integrate handoff detection and escalation into the API query endpoint with comprehensive evaluation and context building.

#### Requirements

1. Generate session ID and initialize conversation flow

2. Execute RAG query and extract answer with full retrieved chunks

3. Create Langfuse span for tracing and get trace ID

4. Run evaluation scores (faithfulness, relevance, confidence) and explicit user request detection

5. Implement handoff decision logic with priority levels (high/normal)

6. Build handoff context payload with all relevant information

7. Send handoff email via background tasks when triggered

8. Return appropriate response (handoff message or normal answer with source nodes)

**File**: `main/routes/routes.py` - `query_rag()`

---

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **generate_handoff_reference_id**: Function generates unique handoff reference IDs following the format "HO-{YYYYMMDD-HHMMSS}-{6-char-hex-uppercase}". Uses UTC timezone and handles optional datetime parameter correctly. Hex portion is uppercase and exactly 6 characters.

2. **evaluate_score**: Function correctly evaluates all handoff trigger conditions in the proper order: no_chunks check, missing evaluation scores, faithfulness threshold, relevance threshold, and keyword detection. Returns appropriate trigger status and reason strings for each condition.

3. **evaluate_confidence_score**: Function uses LLM-as-a-judge to evaluate confidence scores. Properly initializes LLM from Settings, creates structured prompt, extracts numeric score from response (defaults to 50 if parsing fails), and returns trigger status based on CONFIDENCE_THRESHOLD. Handles LLM initialization errors.

4. **evaluate_explicit_user_request**: Function uses LLM-based classification with structured prompt to detect explicit user requests. Returns YES/NO classification correctly, checks response for "YES" case-insensitively, and returns appropriate trigger status with reason when detected.

5. **send_handoff_email**: Function checks for all required SMTP configuration variables and handles missing configuration gracefully with warnings. Creates properly formatted email with subject and body containing all context fields (reference_id, trace_id, timestamp, priority, trigger_reason, user metadata, query history, generated answer, evaluation scores, retrieved chunks, conversation flow). Uses MIMEText, SMTP with STARTTLS, and handles email sending errors.

6. **Query Endpoint Handoff Integration**: Query endpoint implements complete handoff workflow. Session and trace IDs are generated. RAG query executes and chunks are extracted. All evaluators run asynchronously. Handoff decision logic follows priority rules (explicit request → confidence with risk → score-based). Handoff context includes all required fields. Email notifications are sent via background tasks. Normal responses format source nodes correctly.





