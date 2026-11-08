"""
FastAPI Application - Healthcare Analytics Platform
"""
from fastapi import FastAPI
from main.routes import query_routes, ingestion_routes

app = FastAPI(
    title="Healthcare Analytics Platform API",
    description="An intelligent agentic RAG system that combines hospital operational database queries with policy document search",
    version="1.0.0"
)

# Include routers
app.include_router(query_routes.router, prefix="/api", tags=["Query"])
app.include_router(ingestion_routes.router, prefix="/api", tags=["Ingestion"])

@app.get("/")
def root():
    return {
        "message": "Healthcare Analytics Platform API",
        "docs": "/docs",
        "endpoints": {
            "query": "/api/query",
            "upload_documents": "/api/documents/upload",
        }
    }
