"""Test vector retrieval only (no LLM) for a query."""

import asyncio
import os
import sys
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService


async def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "tell me about payment terms"
    document_id = UUID(sys.argv[2]) if len(sys.argv) > 2 else None

    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    engine = create_async_engine(url)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        search = SearchService(session, EmbeddingService())
        hits = await search.search(question, document_id=document_id)
        print(f"Query: {question!r}")
        print(f"Document scope: {document_id or 'all'}")
        print(f"Hits: {len(hits)}\n")
        for hit in hits:
            preview = hit.chunk_text[:120].replace("\n", " ")
            print(f"chunk #{hit.chunk_index}  score={hit.score:.4f}  fallback={hit.metadata.get('threshold_fallback') if hit.metadata else None}")
            print(f"  {preview}...")
            if "payment" in hit.chunk_text.lower():
                idx = hit.chunk_text.lower().index("payment")
                print(f"  [contains payment at char {idx}]")
            print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
