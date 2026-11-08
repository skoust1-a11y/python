"""Unit tests for retrieval merge and deduplication."""

from uuid import uuid4

from llama_index.core.schema import NodeWithScore, TextNode

from app.rag.merge import (
    _dedup_key,
    external_results_to_nodes,
    merge_retrieval_results,
    reciprocal_rank_fusion,
    sql_results_to_nodes,
)
from app.services.sql_query_executor import SqlRetrievalResult
from app.services.sql_retrieval_service import ClauseSummary


def _vector_node(
    document_id: str,
    chunk_index: int,
    *,
    clause_id: str | None = None,
    text: str = "sample chunk text",
    score: float = 0.9,
) -> NodeWithScore:
    metadata = {
        "document_id": document_id,
        "chunk_index": chunk_index,
        "source_type": "vector",
        "score": score,
    }
    if clause_id:
        metadata["clause_id"] = clause_id
    return NodeWithScore(
        node=TextNode(
            id_=f"vec-{document_id}-{chunk_index}",
            text=text,
            metadata=metadata,
        ),
        score=score,
    )


class TestDedupKey:
    def test_clause_id_takes_priority(self) -> None:
        clause_id = str(uuid4())
        node = _vector_node(str(uuid4()), 0, clause_id=clause_id)
        assert _dedup_key(node) == f"clause:{clause_id}"

    def test_chunk_key_for_vector_hits(self) -> None:
        doc_id = str(uuid4())
        node = _vector_node(doc_id, 3)
        assert _dedup_key(node) == f"chunk:{doc_id}:3"


class TestReciprocalRankFusion:
    def test_promotes_items_in_both_lists(self) -> None:
        doc_id = str(uuid4())
        shared = _vector_node(doc_id, 0, text="shared content", score=0.8)
        vector_only = _vector_node(str(uuid4()), 1, text="vector only", score=0.95)
        sql_only = _vector_node(str(uuid4()), -1, text="sql only", score=0.85)

        fused = reciprocal_rank_fusion([[shared, vector_only], [shared, sql_only]])
        assert _dedup_key(fused[0]) == _dedup_key(shared)
        assert len(fused) == 3


class TestMergeRetrievalResults:
    def test_deduplicates_clause_overlap(self) -> None:
        clause_id = uuid4()
        doc_id = uuid4()
        vector = _vector_node(str(doc_id), 2, clause_id=str(clause_id), text="termination clause")

        sql_result = SqlRetrievalResult(
            clauses=[
                ClauseSummary(
                    id=clause_id,
                    document_id=doc_id,
                    clause_number="4.2",
                    title="Termination",
                    content="Either party may terminate...",
                    clause_type="termination",
                    page_number=5,
                    risk_level="medium",
                )
            ]
        )

        merged, stats = merge_retrieval_results([vector], sql_result)
        assert len(merged) == 1
        assert stats.merged_count == 1
        assert stats.vector_input_count == 1
        assert stats.sql_input_count == 1

    def test_sql_only_results_convert_to_nodes(self) -> None:
        sql_result = SqlRetrievalResult(
            clauses=[
                ClauseSummary(
                    id=uuid4(),
                    document_id=uuid4(),
                    clause_number="1",
                    title="Indemnity",
                    content="Indemnification terms...",
                    clause_type="indemnity",
                    page_number=1,
                    risk_level="high",
                )
            ]
        )
        nodes = sql_results_to_nodes(sql_result)
        assert len(nodes) == 1
        assert nodes[0].node.metadata["source_type"] == "sql_clause"
