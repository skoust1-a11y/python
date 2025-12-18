## Multi-Modal Content Processing with LlamaIndex (Tables + Images)

## Project Context

You're building a **Personal Diet Counselling Assistant**, an AI-powered RAG system that helps users get personalized dietary advice, nutrition information, and meal recommendations based on their specific dietary needs and preferences.

This practice focuses on **multi-modal content processing** — extracting **tables and images** from documents (especially PDFs), converting them into text representations (table summaries + image captions), and indexing them alongside regular text for better retrieval.

## Problem Statement

Build a production-ready RAG system that can answer diet-specific queries using document knowledge. The key challenge here is that real documents contain **tables and images** that must be extracted and converted into searchable text.

You will complete the following implementation tasks to build the multi-modal ingestion pipeline:

---

### **Task 1 — Extract Tables from Parsed Text**

#### Goal

Detect markdown tables in parsed document text and return them as structured blocks.

#### Requirements

1. Scan markdown text and detect table blocks
2. Return table blocks with character offsets (start/end) and the table markdown
3. Return an empty list if no tables exist

**File**: `main/service/table_extraction.py` → `find_markdown_tables()` _(currently boilerplate)_

---

### **Task 2 — Summarize Tables and Create Nodes**

#### Goal

Summarize extracted markdown tables and convert them into `TextNode` objects for indexing.

#### Requirements

1. Summarize each table into a concise natural language description using an LLM
2. Create `TextNode` objects for each summary
3. Attach metadata fields such as `source`, `content_type="table_summary"`, and `table_index`
4. Merge any additional metadata into each node

**File**: `main/service/table_processing.py` → `summarize_table()`, `build_nodes_from_tables()` _(currently boilerplate)_

---

### **Task 3 — Extract Images from PDFs**

#### Goal

Extract embedded images from PDF documents and save them to disk for downstream captioning.

#### Requirements

1. Iterate through PDF pages and detect embedded images
2. Save extracted images into an output directory
3. Return a list of extracted image records with `path`, `page`, and `image_index`
4. Return an empty list if no images exist

**File**: `main/service/image_extraction.py` → `extract_images_from_pdf()` _(currently boilerplate)_

---

### **Task 4 — Caption Images**

#### Goal

Generate text captions for extracted images so they can be indexed and retrieved.

#### Requirements

1. Use a vision-capable model (or any image captioning method)
2. Take an image path and an optional prompt
3. Return a concise caption string suitable for indexing

**File**: `main/service/captioning.py` → `generate_caption()` _(currently boilerplate)_

---

### **Task 5 — Integrate Multi-Modal Nodes into Ingestion**

#### Goal

Orchestrate table/image extraction + summarization/captioning and insert the resulting nodes into your vector index.

#### Requirements

1. Parse the document into text/markdown
2. Extract tables and build table summary nodes
3. Extract images and build image caption nodes
4. Ensure metadata is preserved for every node (source, content_type, page/table_index/image_index, diet tags)
5. Insert all nodes into the vector index

**File**: `main/service/rag_service.py` → `process_document()` _(currently boilerplate)_

---

### **Task 6 — Expose Upload Endpoint (API)**

#### Goal

Expose an API endpoint that accepts a document and triggers the multi-modal ingestion pipeline.

#### Requirements

1. Validate filename/extension and max size (10MB)
2. Persist the uploaded bytes for processing
3. Call `process_document()` (ingestion) and return the result
4. Cleanup temporary artifacts

**File**: `main/routes/routes.py` → `upload_document()` _(currently boilerplate)_

---

## Evaluation Criteria

1. Multi-Modal Table Processing: Markdown tables are extracted, summarized, and indexed as separate nodes with `content_type="table_summary"`.
2. Multi-Modal Image Processing: PDF images are extracted, captioned, and indexed as separate nodes with `content_type="image_caption"`.
3. Metadata Preservation: Each node preserves consistent metadata (e.g., `source`, and table/image identifiers like `table_index`, `page`, `image_index`) to support traceability.
4. Upload + Ingestion API: `POST /upload` validates inputs and triggers ingestion, returning a processing summary (once implemented).
5. End-to-End Pipeline: The ingestion pipeline processes text + tables + images and stores everything in the vector database for retrieval.
