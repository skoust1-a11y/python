## Investment Advisor RAG System with Fusion Retrieval and Guardrails

## Project Context

You're building an **Investment Advisor RAG System**, an AI-powered retrieval system that helps users get accurate financial information, investment advice, and policy details from financial documents. The system must handle both exact keyword matching (for terms like "RMD", "401(k)") and semantic understanding (e.g., "risk-averse" → "Conservative profile"), while ensuring security through comprehensive guardrails.

This practice focuses on **fusion retrieval** — combining multiple retrieval methods (BM25 keyword search + Vector semantic search) using Reciprocal Rank Fusion (RRF) for optimal results, and implementing **comprehensive guardrails** for PII protection, input validation, and output sanitization.

## Problem Statement

Build a production-ready RAG system that can answer financial queries using document knowledge with enhanced retrieval accuracy and security. The key challenges are:

1. **Retrieval Accuracy**: Combining keyword-based (BM25) and semantic (vector) search to handle both exact term queries and conceptual queries
2. **Security**: Protecting sensitive information (PII) in both input queries and output responses
3. **Input Validation**: Blocking malicious queries (prompt injection, toxic content)
4. **Output Sanitization**: Automatically redacting PII from generated responses

You will complete the following implementation tasks to build the RAG system with fusion retrieval and guardrails:

---

### **Task 1 — Implement Query API Endpoint**

#### Goal

Create a FastAPI endpoint that accepts user queries and returns structured responses with answers, retrieved chunks, and validation results.

#### Requirements

1. Start a performance timer to measure query processing time
2. Get the active RAG service instance
3. Call the service's query method with the user's query text
4. Transform the service result into a QueryResponse object with proper type mapping
5. Handle exceptions and return appropriate HTTP error responses

**File**: `main/routes/query_routes.py` → `query()` _(currently boilerplate)_

---

### **Task 2 — Initialize Fusion Retrieval System**

#### Goal

Set up the fusion retrieval infrastructure by creating vector and BM25 retrievers and combining them using QueryFusionRetriever.

#### Requirements

1. Create a StorageContext from the vector store
2. Create a VectorStoreIndex from the vector store and storage context
3. Create a vector retriever from the index with configured similarity top k
4. Load all nodes from the vector store for BM25 retriever (with error handling)
5. Create BM25 retriever if nodes are available, otherwise set to None
6. Create a QueryFusionRetriever combining both retrievers with RRF mode
7. Create a RetrieverQueryEngine from the fusion retriever

**File**: `main/service/fusion_retrieval.py` → `_init_retrievers()` _(currently boilerplate)_

---

### **Task 3 — Implement Query and Retrieve Methods**

#### Goal

Implement methods to query the fusion retrieval system for answers and retrieve relevant document chunks.

#### Requirements

1. **Query Method**: Call the query engine with query text and convert the result to a string
2. **Retrieve Method**: Use the fusion retriever to get relevant nodes, then transform each node into a RetrievedChunk object by extracting text, score (with getattr fallback), and source from metadata (filename or source_path)

**File**: `main/service/fusion_retrieval.py` → `query()`, `retrieve()` _(currently boilerplate)_

---

### **Task 4 — Initialize Guardrails Validator**

#### Goal

Set up the Guardrails Hub DetectPII validator for PII detection and redaction.

#### Requirements

1. Initialize `_pii_guard` to None
2. Import Guard and DetectPII from guardrails library
3. Create a Guard instance and configure it with DetectPII to detect various PII entity types (EMAIL_ADDRESS, PHONE_NUMBER, US_SSN, CREDIT_CARD, US_PASSPORT, US_DRIVER_LICENSE, PERSON, LOCATION, DATE_TIME)
4. Set `on_fail="fix"` for automatic redaction
5. Handle exceptions gracefully - if initialization fails, keep `_pii_guard` as None

**File**: `main/service/guardrails.py` → `__init__()` _(currently boilerplate)_

---

### **Task 5 — Implement Input Validation**

#### Goal

Validate user input queries to ensure they are not empty or only whitespace.

#### Requirements

1. Check if the input text is empty or contains only whitespace characters
2. Return `InputDecision(allowed=False, reason="Empty query")` if input is invalid
3. Return `InputDecision(allowed=True, reason=None)` if input is valid

**File**: `main/service/guardrails.py` → `decide_input()` _(currently boilerplate)_

---

### **Task 6 — Implement Output Sanitization**

#### Goal

Validate and sanitize output text using the Guardrails Hub DetectPII validator to detect and redact PII.

#### Requirements

1. Initialize tracking variables (pii_summaries list, pii_detected boolean, output_sanitized boolean, sanitized text)
2. If `_pii_guard` is available, validate the text through the guard
3. Extract validated output from the result and compare with original text
4. If PII was detected and redacted, update tracking variables and add summary message
5. Handle validation errors gracefully by keeping original text
6. Return `OutputDecision` with all validation results (blocked, reason, sanitized_text, pii_detected, pii_summaries, output_sanitized)

**File**: `main/service/guardrails.py` → `validate_and_sanitize_output()` _(currently boilerplate)_

---

### **Task 7 — Initialize RAG Service**

#### Goal

Set up the RAG service by creating the vector store, fusion retrieval service, and validator.

#### Requirements

1. Store instance variables (table_name, similarity_top_k)
2. Create PGVectorStore from environment variables (host, port, database, user, password, table_name, embed_dim)
3. Initialize FusionRetrievalService with the vector store and configuration
4. Set up the validator (use provided validator or get from app.py using get_validator function)

**File**: `main/service/rag_service.py` → `__init__()` _(currently boilerplate)_

---

### **Task 8 — Implement RAG Query Orchestration**

#### Goal

Orchestrate the complete RAG pipeline: input validation → retrieval → answer generation → output sanitization.

#### Requirements

1. Initialize validation_results dictionary with default values (input_allowed, input_block_reason, pii_detected, pii_summaries, output_sanitized, output_blocked, output_block_reason)
2. Validate input using validator's decide_input method
3. If input is blocked, return early with blocked response including validation results
4. Try to retrieve and generate answer using retrieval service (query and retrieve methods)
5. Handle retrieval errors gracefully (e.g., no documents available) and return appropriate error response
6. Validate and sanitize output using validator's validate_and_sanitize_output method
7. Update validation_results with output validation results
8. Return final result dictionary with query, sanitized answer, retrieved nodes, and validation results

**File**: `main/service/rag_service.py` → `query()` _(currently boilerplate)_

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **Fusion Retrieval Initialization**: The fusion retrieval system successfully initializes with both vector and BM25 retrievers (when nodes are available), combines them using QueryFusionRetriever with RRF mode, and creates a query engine.

2. **Query and Retrieve Methods**: The query method returns string answers from the query engine, and the retrieve method returns a list of RetrievedChunk objects with proper text, score, and source extraction from node metadata.

3. **Guardrails Initialization**: The GuardrailsValidator successfully initializes with DetectPII validator configured for multiple PII entity types, with graceful error handling if initialization fails.

4. **Input Validation**: The decide_input method correctly identifies empty or whitespace-only queries and returns appropriate InputDecision objects.

5. **Output Sanitization**: The validate_and_sanitize_output method detects PII in output text, redacts it using the guard, tracks detection status, and returns OutputDecision with all validation results.

6. **End-to-End Pipeline**: The complete system processes queries through input validation → fusion retrieval → answer generation → output sanitization, returning structured responses with retrieved chunks and validation results.
