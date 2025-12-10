# RAG Query Pipeline — Semantic Retrieval & Answer Generation

## Project Context

You're building **Smart Auto Advisor**, an AI-powered conversational assistant for car manufacturers that helps customers get instant answers about vehicle models, features, pricing, and availability.

This practice builds on the previous practices to create a complete query system that retrieves relevant context from the vector database and generates accurate, sourced answers using LLMs.

## Problem Statement

A RAG system needs to answer user questions by retrieving relevant context from the vector database and generating accurate, sourced responses. The system must handle queries efficiently, provide citations, and scale to serve multiple users simultaneously. Without a proper query pipeline, you can't transform stored embeddings into actionable answers.

You will complete three tasks to build this query pipeline:

---

### **Task 1 — Semantic Retrieval and Vector Search**

#### Goal

Implement semantic retrieval to find relevant document chunks using vector similarity search.

#### Requirements

Create a retrieval service that:

- Connects to PostgreSQL with PgVector (from previous practice)
- Performs similarity search using cosine distance
- Retrieves top-k most relevant document chunks
- Returns chunks with source metadata and chunk IDs
- Handles empty results gracefully

---

### **Task 2 — RAG Chain and LLM Integration**

#### Goal

Build a RAG chain that combines retrieval, prompt assembly, and LLM generation using LangChain LCEL.

#### Requirements

1. **Prompt Templates**

   - Create production-ready prompt templates
   - Format retrieved chunks into structured prompts
   - Include instructions to prevent hallucination
   - Add fallback messages for insufficient context

2. **LLM Service**

   - Initialize Azure OpenAI LLM (gpt-4o-mini or similar)
   - Configure temperature and max tokens appropriately
   - Handle LLM errors gracefully

3. **RAG Chain**
   - Build chain using LangChain Expression Language (LCEL)
   - Combine retriever → document formatter → prompt template → LLM → output parser
   - Ensure proper error handling throughout the chain

---

### **Task 3 — REST API and Query Service**

#### Goal

Build a complete query pipeline with REST API endpoints for querying the RAG system.

#### Requirements

1. **Query Service**

   - Implement query execution with error handling
   - Return answers with source citations
   - Handle graceful failures when context is insufficient
   - Include comprehensive logging

2. **REST API Endpoints**

   - `POST /query` - Full RAG query with retrieval and LLM generation
   - `POST /retrieve` - Semantic search only (retrieval without LLM)
   

3. **Response Format**
   - Include question, answer, sources, and metadata
   - Provide source citations with chunk IDs and source file names
   - Return appropriate HTTP status codes
   - Include timestamps in responses

---

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. Semantic retrieval is implemented using PostgreSQL with PgVector for similarity search

2. RAG chain is built using LangChain Expression Language (LCEL) with proper component composition

3. Prompt templates are production-ready with hallucination prevention and fallback handling

4. LLM service is properly initialized with Azure OpenAI and integrated into the RAG chain

5. Source citations are included in query responses with chunk IDs and source file metadata

6. The pipeline performs end-to-end RAG queries: retrieval → context assembly → LLM generation → response formatting
