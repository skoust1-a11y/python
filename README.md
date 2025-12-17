# Product Manual RAG System

## Project Context

You're building a **Product Manual RAG System**, an AI-powered system that helps users get answers to questions about product features, installation, configuration, troubleshooting, and usage instructions.

This practice focuses on **RAG system evaluation** — implementing automated evaluation pipelines using Langfuse and LLM-as-a-judge techniques. You'll learn how to create evaluation datasets, build evaluators that measure faithfulness and answer relevance, and run comprehensive evaluation pipelines that track quality metrics and SLO compliance.

## Problem Statement

Build a RAG system with automated evaluation capabilities. The system must support document indexing, query processing, and systematic evaluation using structured datasets. You need to implement LLM-as-a-judge evaluators that measure answer quality across multiple dimensions (faithfulness, relevance) and generate comprehensive evaluation reports.

You will complete multiple implementation tasks to build this evaluated RAG system:

---

### **Task 1 — Create Evaluation Dataset**

#### Goal

Build functionality to create structured evaluation datasets in Langfuse with test questions and expected answers.

#### Requirements

1. Implement `get_langfuse_client()` to initialize Langfuse client from environment variables

2. Implement `create_dataset()` to create dataset in Langfuse with metadata

3. Implement `add_items()` to add 10 test questions (3 easy, 4 medium, 3 hard) with metadata

4. Implement `main()` to orchestrate dataset creation

**File**: `main/evaluation/dataset.py`

---

### **Task 2 — Implement LLM-as-a-Judge Evaluators and Pipeline**

#### Goal

Build evaluators that use LLM-as-a-judge to score answer quality and implement the complete evaluation pipeline.

#### Requirements

1. Implement `evaluate_faithfulness_score()` using LLM-as-a-judge

2. Implement `evaluate_answer_relevance()` using LLM-as-a-judge

3. Implement `query_with_evaluation()` to execute query and run evaluators

4. Implement `run_dataset_evaluation()` to run evaluation on dataset and calculate metrics

**File**: `main/evaluation/dataset_evaluation.py`

---

### **Task 3 — Add Evaluation to Query Endpoint**

#### Goal

Integrate automatic evaluation and tracing into the API query endpoint.

#### Requirements

1. Import Langfuse client and evaluator functions

2. Extract full context from source_nodes

3. Create Langfuse span and run evaluators asynchronously

4. Update span with scores and handle errors

**File**: `main/routes/routes.py` - `query_rag()`

---

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **Evaluation Dataset Creation**: Langfuse dataset is created with 10 test questions (3 easy, 4 medium, 3 hard) with proper metadata (category, difficulty, manual_section) and expected outputs. Dataset items are successfully added to Langfuse using langfuse.create_dataset_item().

2. **LLM-as-a-Judge Evaluators**: Faithfulness and answer relevance evaluators are implemented with structured prompts, score extraction from LLM judgments, and Langfuse score attachment. Evaluators return scores in 0.0-1.0 range and handle errors gracefully.

3. **Evaluation Pipeline**: Complete evaluation pipeline runs queries on all dataset items, executes evaluators asynchronously, calculates aggregate metrics (average scores, SLO compliance), and displays comprehensive results. All traces and scores are logged to Langfuse.

4. **Query Endpoint Evaluation**: Query endpoint integrates automatic evaluation and tracing. Full context is extracted for evaluation, Langfuse spans are created, evaluators run asynchronously, and scores are attached to traces. Evaluation errors don't break the API.



