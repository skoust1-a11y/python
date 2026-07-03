"""Inspect indexed document chunks (dev diagnostic)."""

import asyncio
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


async def main() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    engine = create_async_engine(url)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        doc_count = await session.scalar(text("SELECT count(*) FROM documents"))
        emb_count = await session.scalar(text("SELECT count(*) FROM document_embeddings"))
        print(f"documents: {doc_count}")
        print(f"embeddings: {emb_count}")

        result = await session.execute(
            text(
                """
                SELECT d.filename, d.title, de.chunk_index, left(de.chunk_text, 400)
                FROM document_embeddings de
                JOIN documents d ON d.id = de.document_id
                ORDER BY d.created_at DESC, de.chunk_index
                """
            )
        )
        for filename, title, chunk_index, preview in result.all():
            print(f"\n--- {title or filename} | chunk {chunk_index} ---")
            print(preview)

        payment = await session.execute(
            text(
                """
                SELECT chunk_index, length(chunk_text)
                FROM document_embeddings
                WHERE chunk_text ILIKE '%payment%'
                """
            )
        )
        rows = payment.all()
        print(f"\npayment term chunks: {len(rows)}")
        for chunk_index, length in rows:
            print(f"  chunk {chunk_index}, length {length}")

        payment_ctx = await session.execute(
            text(
                """
                SELECT chunk_index,
                       position(lower('payment') in lower(chunk_text)) as pos
                FROM document_embeddings
                WHERE chunk_text ILIKE '%payment%'
                ORDER BY chunk_index
                """
            )
        )
        for chunk_index, pos in payment_ctx.all():
            result2 = await session.execute(
                text(
                    "SELECT substring(chunk_text from :pos for 500) "
                    "FROM document_embeddings WHERE chunk_index = :idx"
                ),
                {"pos": max(1, int(pos)), "idx": chunk_index},
            )
            snippet = result2.scalar()
            print(f"\n--- payment snippet chunk {chunk_index} ---")
            print(snippet)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
