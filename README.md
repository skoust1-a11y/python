## Project Context

You're building **Smart Auto Advisor**, an AI-powered conversational assistant for car manufacturers that helps customers get instant answers about vehicle models, features, pricing, and availability.

This practice builds on the previous practice to create a complete document ingestion pipeline that transforms raw documents (PDFs, HTML, text files) into searchable vector embeddings.

## Problem Statement

Real-world RAG systems need to process diverse document formats (PDFs, web pages, text files) and convert them into searchable vectors. Documents must be split into manageable chunks, embedded, and stored with metadata for accurate retrieval. Without a proper ingestion pipeline, you can't populate your knowledge base with company documents, product specs, or customer data.

You will complete three tasks to build this ingestion pipeline:

---

### **Task 1 — Document Loading and Processing**

#### Goal

Load documents from multiple sources (PDF, HTML, TXT, Web) and process them for ingestion.

#### Requirements

Create a document processing service that:

- Automatically detects file type
- Routes files to appropriate loaders
- Handles errors gracefully
- Preserves source file metadata

### **Task 2 — Document Chunking and Embedding**

#### Goal

Split documents into manageable chunks and generate vector embeddings.

#### Requirements

- Implement intelligent chunking

- Generate embeddings

### **Task 3 — Complete Pipeline and REST API**

#### Goal

Build a complete ingestion pipeline with REST API endpoints for document upload and querying.

#### Requirements

- Create pipeline orchestration service

  - Coordinate document loading, chunking, and embedding

2. Implement REST API endpoints

# Evaluation Criteria

Ensure you evaluate your solution against the below criteria

1. Proper Document loader for pdf, txt, html are used
2. Document chunking is done using `RecursiveCharacterTextSplitter`
3. Chunks are properly embedded and stored in Postgres Database with pgVector
4. The pipeline performs basic semantic query
