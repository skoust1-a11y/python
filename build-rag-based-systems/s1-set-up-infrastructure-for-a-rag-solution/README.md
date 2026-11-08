## Project Context

You're building **Smart Auto Advisor**, an AI-powered conversational assistant for car manufacturers that helps customers get instant answers about vehicle models, features, pricing, and availability.

This practice focuses on the **foundation layer** — setting up the vector database infrastructure and understanding how embeddings work. You'll learn how to convert text into vector embeddings, store them in PostgreSQL with PgVector, and perform semantic similarity searches.

## Problem Statement

Establish the foundational understanding of how text is converted into vector embeddings, how to store and retrieve embeddings efficiently, and how semantic similarity search works. Without a proper vector database infrastructure, you can't build a functional RAG system that retrieves relevant information from knowledge bases.

You will complete three tasks to build this foundation:

---

### **Task 1 — Setup PostgreSQL with PgVector Extension**

#### Goal

Prepare a PostgreSQL database with vector search capabilities.

#### Requirements

1. Install PostgreSQL on your system
2. Enable the PgVector extension

---

### **Task 2 — Generate and Store Embeddings**

#### Goal

Create vector embeddings for sample automotive text(sample_data.py) and store them in the database using(embedding_setup.py).

#### Requirements

1. Configure Azure OpenAI credentials in `.env`
2. Initialize Azure OpenAI embeddings (1536 dimensions using text-embedding-3-small)
3. Generate embeddings for sample automotive text
4. Create a PGVector vectorstore connection
5. Store embeddings in PostgreSQL database with metadata

---

### **Task 3 — Complete Pipeline and REST API**

#### Goal

Build a complete infrastructure setup with REST API endpoints for document upload and querying.

#### Requirements

1. Create pipeline orchestration service:

   - Coordinate embedding generation and storage
   - Handle CRUD operations (Create, Read)
   - Provide error handling and logging

2. Implement REST API endpoints:

   - Document upload endpoint
   - Query endpoint for similarity search

3. Run and Test the Application

---

# Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. PostgreSQL database is properly configured with PgVector extension enabled
2. Azure OpenAI embeddings are correctly initialized and configured (text-embedding-3-small, 1536 dimensions)
3. Embeddings are properly generated and stored in PostgreSQL database with pgVector
4. The pipeline performs basic semantic query operations successfully
