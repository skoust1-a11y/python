from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import defer

from app.core.config import get_settings
from app.core.constants import HOUSE_TYPES, NOTE_KIND, POLICY_DOCS, POLICY_DOCS_BY_ID, STOCK_KINDS
from app.core.db import FinanceSessionLocal, StockSessionLocal
from app.core.ids import new_doc_id
from app.core.llm import embed_texts
from app.models import EquityUniverse, Holding, PolicyChunk, Portfolio, StockChunk, StockDocument, UserDocument
from app.profiles import DEFAULT_PROFILE_ID, normalize_profile_id

MAX_PDF_BYTES = 5_000_000
DOC_USE_CASES = HOUSE_TYPES
_USE_CASE_PATHS = {
    "strategy": {"C1_RAG", "C3_HYBRID", "C4_HIGH_RISK"},
    "risk": {"C3_HYBRID", "C4_HIGH_RISK"},
    "regulatory": {"C1_RAG", "C3_HYBRID", "C4_HIGH_RISK"},
    "research": {"C1_RAG", "C4_HIGH_RISK"},
    "evaluation": {"C1_RAG", "C3_HYBRID"},
    "framework": {"C3_HYBRID", "C4_HIGH_RISK"},
    "matrix": {"C1_RAG", "C3_HYBRID", "C4_HIGH_RISK"},
    "all": {"C1_RAG", "C3_HYBRID", "C4_HIGH_RISK"},
    "C1_RAG": {"C1_RAG"},
    "C3_HYBRID": {"C3_HYBRID"},
    "C4_HIGH_RISK": {"C4_HIGH_RISK"},
}
_USE_CASE_ROLE = {
    "strategy": "strategy",
    "risk": "policy",
    "regulatory": "policy",
    "research": "policy",
    "evaluation": "policy",
    "framework": "policy",
    "matrix": "matrix",
}
_USE_CASE_CATEGORY = {
    "strategy": "strategy",
    "risk": "risk",
    "regulatory": "regulatory",
    "research": "market",
    "evaluation": "monitoring",
    "framework": "framework",
    "matrix": "framework",
}
_SAFE = re.compile(r"[^a-zA-Z0-9_-]+")
_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.&-]{0,19}$")


def normalize_symbol(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().upper()
    if not text:
        return None
    return text if _SYMBOL.fullmatch(text) else None


class DocumentIngestError(ValueError):
    pass


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2]


_STOP = frozenset(
    "the and for are but not you all any can had her was one our out has him his how its may new now old see two "
    "way who did get got let put say she too use what when where which while with would could should about into "
    "from that this those these there their them they then than your yours have does just like tell give show "
    "much many some more most very also only such here other each over under after before".split()
)


def corpus_coverage(text: str) -> Optional[float]:
    """Share of the query's content words found in the policy corpus or portfolio names; None when it has none."""
    words = [t for t in _tokens(text) if t not in _STOP]
    if not words:
        return None
    vocab: Set[str] = set()
    session = FinanceSessionLocal()
    try:
        for stmt in (
            select(PolicyChunk.chunk_text, PolicyChunk.section, PolicyChunk.doc_title),
            select(Portfolio.portfolio_name, Portfolio.portfolio_manager, Portfolio.benchmark_index),
            select(Holding.asset_name, Holding.sector),
            select(EquityUniverse.symbol, EquityUniverse.sector),
        ):
            for row in session.execute(stmt):
                vocab.update(_tokens(" ".join(filter(None, row))))
    finally:
        session.close()
    return sum(w in vocab for w in words) / len(words)


def _vec(raw: Any) -> Optional[List[float]]:
    if not raw:
        return None
    if isinstance(raw, list):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return None
    if not isinstance(data, list) or not data:
        return None
    return [float(x) for x in data]


def _dump_vec(vec: List[float]) -> str:
    return json.dumps([round(float(x), 6) for x in vec], separators=(",", ":"))


def _cosine(left: List[float], right: List[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    na = sum(a * a for a in left) ** 0.5
    nb = sum(b * b for b in right) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _attach_embeddings(chunks: List[Any]) -> int:
    vecs = embed_texts([chunk.chunk_text for chunk in chunks])
    for chunk, vec in zip(chunks, vecs):
        chunk.embedding = _dump_vec(vec)
    return len(vecs)


def _safe_token(value: str) -> str:
    return _SAFE.sub("", value)[:80]


def _user_docs(session, owner_id: str) -> List[UserDocument]:
    return list(
        session.execute(select(UserDocument).where(UserDocument.owner_id == owner_id)).scalars()
    )


def document_meta(doc_id: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
    return _meta_for(doc_id, owner_id)


def _meta_for(doc_id: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
    system = POLICY_DOCS_BY_ID.get(doc_id)
    if system:
        return dict(system)
    if not owner_id:
        return {}
    session = FinanceSessionLocal()
    try:
        row = session.get(UserDocument, doc_id)
        if row is not None and row.owner_id == owner_id:
            return {
                "doc_id": row.doc_id,
                "doc_title": row.doc_title,
                "filename": row.filename,
                "category": row.category,
                "role": row.role,
                "use_case": row.use_case or "all",
                "origin": "user",
            }
    finally:
        session.close()
    stock = StockSessionLocal()
    try:
        row = stock.get(StockDocument, doc_id)
        if row is None or row.owner_id != owner_id:
            return {}
        kind = row.kind or "ar"
        return {
            "doc_id": row.doc_id,
            "doc_title": row.doc_title,
            "filename": row.filename,
            "category": "research",
            "role": "policy",
            "use_case": kind,
            "kind": kind,
            "symbol": row.symbol,
            "origin": "user",
        }
    finally:
        stock.close()


def _use_case_matches(stored: Optional[str], category: Optional[str]) -> bool:
    if not category or category not in ("C1_RAG", "C3_HYBRID", "C4_HIGH_RISK"):
        return False
    value = stored or "all"
    paths = _USE_CASE_PATHS.get(value)
    if paths is not None:
        return category in paths
    return category in {part.strip() for part in value.split(",") if part.strip()}


def visible_doc_ids(
    owner_id: Optional[str] = None,
    category: Optional[str] = None,
    symbol: Optional[str] = None,
    profile_id: Optional[str] = None,
) -> Set[str]:
    ticker = normalize_symbol(symbol)
    profile = normalize_profile_id(profile_id)
    if ticker:
        if not owner_id:
            return set()
        session = StockSessionLocal()
        try:
            by_kind: Dict[str, str] = {}
            rows = list(
                session.execute(
                    select(StockDocument)
                    .where(
                        StockDocument.owner_id == owner_id,
                        StockDocument.symbol == ticker,
                        StockDocument.profile_id == profile,
                    )
                    .order_by(StockDocument.created_at.desc())
                ).scalars()
            )
            for row in rows:
                kind = row.kind or "ar"
                if kind == NOTE_KIND or kind in by_kind:
                    continue
                by_kind[kind] = row.doc_id
            return set(by_kind.values())
        finally:
            session.close()
    ids = {doc["doc_id"] for doc in POLICY_DOCS}
    if not owner_id:
        return ids
    session = FinanceSessionLocal()
    try:
        mine = [
            row
            for row in _user_docs(session, owner_id)
            if (row.profile_id or DEFAULT_PROFILE_ID) == profile
        ]
        if profile != DEFAULT_PROFILE_ID:
            by_uc = {row.use_case: row.doc_id for row in mine if row.use_case in HOUSE_TYPES}
            ids = set()
            for meta in POLICY_DOCS:
                ids.add(by_uc.get(meta["use_case"], meta["doc_id"]))
            return ids
        ids.update(row.doc_id for row in mine if _use_case_matches(row.use_case, category))
        return ids
    finally:
        session.close()


def retrieve(
    query: str,
    top_k: Optional[int] = None,
    owner_id: Optional[str] = None,
    category: Optional[str] = None,
    symbol: Optional[str] = None,
    profile_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    settings = get_settings()
    allowed = visible_doc_ids(owner_id, category, symbol, profile_id)
    ticker = normalize_symbol(symbol)
    if category == "C4_HIGH_RISK" and not ticker:
        # High-risk decisions are governed by exposure limits, the escalation matrix and approval tiers (UC-11).
        allowed = {d for d in allowed if _meta_for(d, owner_id).get("use_case") not in ("strategy", "regulatory", "research", "evaluation")}
    if not allowed:
        return []
    session = StockSessionLocal() if ticker else FinanceSessionLocal()
    model = StockChunk if ticker else PolicyChunk
    in_scope = model.doc_id.in_(allowed)
    try:
        q_vec = None
        # A partially embedded index (one PDF's embed call failed) would rank only the embedded docs; go lexical-only.
        if not session.execute(select(model.chunk_id).where(in_scope, model.embedding.is_(None)).limit(1)).first():
            q_vecs = embed_texts([query])
            q_vec = q_vecs[0] if q_vecs else None
        dense = _pg_dense(session, model.__tablename__, allowed, q_vec) if q_vec else {}
        stmt = select(model).where(in_scope)
        if dense is not None:
            stmt = stmt.options(defer(model.embedding))
        chunks = list(session.execute(stmt).scalars())
    finally:
        session.close()
    if dense is None:
        dense = {}
        for chunk in chunks:
            c_vec = _vec(chunk.embedding)
            if c_vec:
                dense[chunk.chunk_id] = _cosine(q_vec, c_vec)
    q_tokens = set(_tokens(query))
    lexical: Dict[str, float] = {}
    for chunk in chunks:
        c_tokens = _tokens(chunk.chunk_text + " " + (chunk.section or "") + " " + (chunk.doc_title or ""))
        if not c_tokens:
            continue
        score = len(q_tokens & set(c_tokens)) / float(max(len(q_tokens), 1))
        if score <= 0 and any(tok in chunk.chunk_text.lower() for tok in q_tokens):
            score = settings.retrieval_weak_score
        if score > 0:
            lexical[chunk.chunk_id] = score
    fused = _rrf(
        [(dense, settings.retrieval_vector_weight), (lexical, settings.retrieval_lexical_weight)],
        settings.retrieval_rrf_k,
    )
    scored: List[Dict[str, Any]] = []
    for chunk in chunks:
        score = max(dense.get(chunk.chunk_id, 0.0), lexical.get(chunk.chunk_id, 0.0))
        if score < settings.retrieval_min_score:
            continue
        meta = _meta_for(chunk.doc_id, owner_id)
        scored.append(
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "doc_title": chunk.doc_title,
                "doc_category": chunk.doc_category,
                "section": chunk.section or "",
                "page": int(chunk.page or 0),
                "chunk_text": chunk.chunk_text,
                "score": round(min(score, 1.0), 3),
                "filename": meta.get("filename"),
                "origin": meta.get("origin", "system"),
                "role": meta.get("role"),
            }
        )
    scored.sort(key=lambda item: fused.get(item["chunk_id"], 0.0), reverse=True)
    k = top_k if top_k is not None else settings.retrieval_top_k
    if not scored:
        return []
    # Keep the top doc plus docs backed by 2+ of the top-k chunks; a lone stray chunk usually cites an off-topic doc.
    counts = Counter(item["doc_id"] for item in scored[:k])
    keep = {scored[0]["doc_id"]} | {doc for doc, n in counts.items() if n >= 2}
    return [item for item in scored if item["doc_id"] in keep][:k]


def _pg_dense(session, table: str, allowed: Set[str], q_vec: List[float]) -> Optional[Dict[str, float]]:
    """Cosine scores computed by pgvector; None when not on Postgres or the vector column is missing."""
    if session.get_bind().dialect.name != "postgresql":
        return None
    sql = text(
        "SELECT chunk_id, 1 - (embedding_vec <=> CAST(:q AS vector)) FROM {} "
        "WHERE embedding_vec IS NOT NULL AND vector_dims(embedding_vec) = :dim AND doc_id = ANY(:ids)".format(table)
    )
    try:
        rows = session.execute(sql, {"q": _dump_vec(q_vec), "dim": len(q_vec), "ids": list(allowed)})
        return {chunk_id: float(score) for chunk_id, score in rows}
    except SQLAlchemyError:
        session.rollback()
        return None


def _rrf(rankings: List[Tuple[Dict[str, float], float]], k: int) -> Dict[str, float]:
    """Weighted reciprocal rank fusion over {chunk_id: score} maps."""
    fused: Dict[str, float] = {}
    for scores, weight in rankings:
        for rank, chunk_id in enumerate(sorted(scores, key=scores.get, reverse=True), 1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + weight / (k + rank)
    return fused


def corpus_root() -> Path:
    from app.core.storage import get_corpus_store

    return get_corpus_store().root()


def user_pdf_path(owner_id: str, doc_id: str) -> Path:
    return corpus_root() / "uploads" / _safe_token(owner_id) / "{}.pdf".format(_safe_token(doc_id))


def stock_pdf_path(owner_id: str, doc_id: str) -> Path:
    return corpus_root() / "uploads" / "stocks" / _safe_token(owner_id) / "{}.pdf".format(_safe_token(doc_id))


def pdf_path(filename: str) -> Optional[Path]:
    path = corpus_root() / filename
    return path if path.is_file() else None


def resolve_pdf(doc_id: str, owner_id: Optional[str] = None) -> Optional[Path]:
    meta = POLICY_DOCS_BY_ID.get(doc_id)
    if meta:
        return pdf_path(meta["filename"])
    if not owner_id:
        return None
    path = user_pdf_path(owner_id, doc_id)
    if path.is_file():
        return path
    stock = stock_pdf_path(owner_id, doc_id)
    return stock if stock.is_file() else None


def _chunk_out(chunk: PolicyChunk) -> Dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "doc_title": chunk.doc_title,
        "doc_category": chunk.doc_category,
        "section": chunk.section or "",
        "page": int(chunk.page or 0),
        "chunk_text": chunk.chunk_text,
    }


def chunks_for_doc(doc_id: str) -> List[Dict[str, Any]]:
    session = FinanceSessionLocal()
    try:
        rows = session.execute(
            select(PolicyChunk)
            .where(PolicyChunk.doc_id == doc_id)
            .order_by(PolicyChunk.page, PolicyChunk.chunk_id)
        ).scalars().all()
        if rows:
            return [_chunk_out(row) for row in rows]
    finally:
        session.close()
    stock = StockSessionLocal()
    try:
        rows = stock.execute(
            select(StockChunk)
            .where(StockChunk.doc_id == doc_id)
            .order_by(StockChunk.page, StockChunk.chunk_id)
        ).scalars().all()
        return [_chunk_out(row) for row in rows]
    finally:
        stock.close()


def chunks_grouped() -> Dict[str, List[Dict[str, Any]]]:
    session = FinanceSessionLocal()
    try:
        rows = session.execute(
            select(PolicyChunk).order_by(PolicyChunk.page, PolicyChunk.chunk_id)
        ).scalars().all()
    finally:
        session.close()
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.doc_id, []).append(_chunk_out(row))
    return grouped


def user_document_records(owner_id: str, profile_id: Optional[str] = None) -> List[Dict[str, Any]]:
    profile = normalize_profile_id(profile_id)
    session = FinanceSessionLocal()
    try:
        return [
            {
                "doc_id": row.doc_id,
                "doc_title": row.doc_title,
                "filename": row.filename,
                "category": row.category,
                "role": row.role,
                "use_case": row.use_case or "all",
                "origin": "user",
            }
            for row in _user_docs(session, owner_id)
            if (row.profile_id or DEFAULT_PROFILE_ID) == profile
        ]
    finally:
        session.close()


def house_document_records(owner_id: str, profile_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """One document per house type — the one currently in use (upload wins over built-in)."""
    profile = normalize_profile_id(profile_id)
    mine = {row["use_case"]: row for row in user_document_records(owner_id, profile) if row.get("use_case") in HOUSE_TYPES}
    rows = []
    for meta in POLICY_DOCS:
        rows.append(mine.get(meta["use_case"]) or dict(meta))
    return rows


def stock_document_records(owner_id: str, symbol: str, profile_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """One filing per kind (ar/concall/ppt) plus the current note — latest wins."""
    ticker = normalize_symbol(symbol)
    profile = normalize_profile_id(profile_id)
    if not ticker:
        return []
    session = StockSessionLocal()
    try:
        rows = list(
            session.execute(
                select(StockDocument)
                .where(
                    StockDocument.owner_id == owner_id,
                    StockDocument.symbol == ticker,
                    StockDocument.profile_id == profile,
                )
                .order_by(StockDocument.created_at.desc())
            ).scalars()
        )
    finally:
        session.close()
    current: Dict[str, Any] = {}
    for row in rows:
        kind = row.kind or "ar"
        if kind in current:
            continue
        current[kind] = {
            "doc_id": row.doc_id,
            "doc_title": row.doc_title,
            "filename": row.filename,
            "category": "research",
            "role": "policy",
            "use_case": kind,
            "kind": kind,
            "symbol": row.symbol,
            "origin": "user",
        }
    order = list(STOCK_KINDS) + ([NOTE_KIND] if NOTE_KIND in current else [])
    return [current[k] for k in order if k in current]


def _extract_chunks(path: Path, doc_id: str, title: str, category: str, model=PolicyChunk, known=None):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentIngestError("PDF support is not installed") from exc
    settings = get_settings()
    size = settings.chunk_size_chars
    overlap = min(settings.chunk_overlap_chars, max(size - 1, 0))
    step = max(size - overlap, 1)
    floor = settings.chunk_min_chars
    reader = PdfReader(str(path))
    extracted = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if len(text) < floor:
            continue
        for part_i, start in enumerate(range(0, len(text), step)):
            piece = text[start : start + size].strip()
            if len(piece) < floor:
                continue
            extracted.append(
                model(
                    chunk_id="pdf_{}_{}_{}".format(doc_id[:12], index, part_i),
                    doc_id=doc_id,
                    doc_title=title,
                    doc_category=category,
                    section="page {}".format(index),
                    page=index,
                    chunk_text=piece,
                    token_count=len(piece.split()),
                    embedding=(known or {}).get(piece),
                )
            )
    _attach_embeddings([chunk for chunk in extracted if not chunk.embedding])
    return extracted


def reindex_from_pdfs() -> int:
    """Replace system policy_chunks from the 7 PDFs; leave user uploads in place."""
    root = corpus_root()
    session = FinanceSessionLocal()
    try:
        known = dict(session.execute(select(PolicyChunk.chunk_text, PolicyChunk.embedding).where(PolicyChunk.embedding.isnot(None))).all())
    finally:
        session.close()
    extracted: List[PolicyChunk] = []
    for meta in POLICY_DOCS:
        path = root / meta["filename"]
        if not path.exists():
            continue
        try:
            extracted.extend(
                _extract_chunks(path, meta["doc_id"], meta["doc_title"], meta["category"], known=known)
            )
        except DocumentIngestError:
            return 0
    if not extracted:
        return 0
    session = FinanceSessionLocal()
    try:
        session.query(PolicyChunk).filter(PolicyChunk.doc_id.in_(list(POLICY_DOCS_BY_ID))).delete(
            synchronize_session=False
        )
        session.add_all(extracted)
        session.commit()
        return len(extracted)
    finally:
        session.close()


def _replace_house_pdf(session, owner_id: str, profile: str, use_case: str) -> None:
    for row in _user_docs(session, owner_id):
        if (row.profile_id or DEFAULT_PROFILE_ID) == profile and row.use_case == use_case:
            session.query(PolicyChunk).filter(PolicyChunk.doc_id == row.doc_id).delete(synchronize_session=False)
            session.delete(row)
            user_pdf_path(owner_id, row.doc_id).unlink(missing_ok=True)


def _replace_stock_pdf(session, owner_id: str, profile: str, symbol: str, kind: str) -> None:
    rows = list(
        session.execute(
            select(StockDocument).where(
                StockDocument.owner_id == owner_id,
                StockDocument.profile_id == profile,
                StockDocument.symbol == symbol,
                StockDocument.kind == kind,
            )
        ).scalars()
    )
    for row in rows:
        session.query(StockChunk).filter(StockChunk.doc_id == row.doc_id).delete(synchronize_session=False)
        session.delete(row)
        stock_pdf_path(owner_id, row.doc_id).unlink(missing_ok=True)


def ingest_user_pdf(
    raw: bytes,
    filename: str,
    owner_id: str,
    title: str,
    use_case: str,
    symbol: Optional[str] = None,
    profile_id: Optional[str] = None,
) -> Dict[str, Any]:
    ticker = normalize_symbol(symbol)
    if symbol and str(symbol).strip() and ticker is None:
        raise DocumentIngestError("symbol must be a ticker like SYNTECH")
    if ticker:
        if use_case == NOTE_KIND:
            raise DocumentIngestError("note is generated output and cannot be uploaded")
        if use_case not in STOCK_KINDS:
            raise DocumentIngestError("ticker document type must be ar, concall, or ppt")
        kind = use_case
        role = "policy"
        category = "research"
    else:
        if use_case not in DOC_USE_CASES:
            raise DocumentIngestError(
                "use case must be strategy, risk, regulatory, research, evaluation, framework, or matrix"
            )
        kind = None
        role = _USE_CASE_ROLE[use_case]
        category = _USE_CASE_CATEGORY[use_case]
    if not raw:
        raise DocumentIngestError("file is empty")
    if len(raw) > MAX_PDF_BYTES:
        raise DocumentIngestError("PDF is larger than 5MB")
    name = (filename or "upload.pdf").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if not name.lower().endswith(".pdf"):
        raise DocumentIngestError("upload a .pdf file")
    profile = normalize_profile_id(profile_id)
    doc_id = new_doc_id()
    dest = (stock_pdf_path if ticker else user_pdf_path)(owner_id, doc_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    heading = (title or Path(name).stem).strip()[:200] or "Uploaded document"
    try:
        chunks = _extract_chunks(dest, doc_id, heading, category, StockChunk if ticker else PolicyChunk)
    except DocumentIngestError:
        dest.unlink(missing_ok=True)
        raise
    if not chunks:
        dest.unlink(missing_ok=True)
        raise DocumentIngestError("could not extract enough text from this PDF")
    session = StockSessionLocal() if ticker else FinanceSessionLocal()
    try:
        if ticker:
            _replace_stock_pdf(session, owner_id, profile, ticker, kind)
            session.add(
                StockDocument(
                    doc_id=doc_id,
                    owner_id=owner_id,
                    symbol=ticker,
                    doc_title=heading,
                    filename=name,
                    kind=kind,
                    profile_id=profile,
                )
            )
        else:
            _replace_house_pdf(session, owner_id, profile, use_case)
            session.add(
                UserDocument(
                    doc_id=doc_id,
                    owner_id=owner_id,
                    doc_title=heading,
                    filename=name,
                    category=category,
                    role=role,
                    use_case=use_case,
                    profile_id=profile,
                )
            )
        session.add_all(chunks)
        session.commit()
    except Exception:
        dest.unlink(missing_ok=True)
        session.rollback()
        raise
    finally:
        session.close()
    return {
        "doc_id": doc_id,
        "doc_title": heading,
        "filename": name,
        "category": category,
        "role": "policy" if ticker else role,
        "use_case": kind if ticker else use_case,
        "kind": kind,
        "symbol": ticker,
        "profile_id": profile,
        "origin": "user",
        "chunk_count": len(chunks),
        "has_file": True,
    }


def filing_counts(owner_id: str, symbols: List[str], profile_id: Optional[str] = None) -> Dict[str, int]:
    profile = normalize_profile_id(profile_id)
    wanted = {normalize_symbol(item) for item in symbols}
    wanted.discard(None)
    if not wanted or not owner_id:
        return {}
    session = StockSessionLocal()
    try:
        counts = {symbol: 0 for symbol in wanted}
        for row in session.execute(
            select(StockDocument.symbol, StockDocument.kind).where(
                StockDocument.owner_id == owner_id,
                StockDocument.profile_id == profile,
                StockDocument.symbol.in_(wanted),
            )
        ):
            if (row.kind or "ar") != NOTE_KIND:
                counts[row.symbol] = counts.get(row.symbol, 0) + 1
        return counts
    finally:
        session.close()


def load_stock_note(owner_id: str, symbol: str, profile_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    ticker = normalize_symbol(symbol)
    if not ticker:
        return None
    profile = normalize_profile_id(profile_id)
    session = StockSessionLocal()
    try:
        row = session.execute(
            select(StockDocument)
            .where(
                StockDocument.owner_id == owner_id,
                StockDocument.symbol == ticker,
                StockDocument.profile_id == profile,
                StockDocument.kind == NOTE_KIND,
            )
            .order_by(StockDocument.created_at.desc())
        ).scalars().first()
        if row is None or not row.body:
            return None
        return {"body": row.body, "created_at": row.created_at, "doc_title": row.doc_title}
    finally:
        session.close()


def filings_newer_than_note(owner_id: str, symbol: str, profile_id: Optional[str], note_at) -> bool:
    ticker = normalize_symbol(symbol)
    if not ticker or note_at is None:
        return False
    profile = normalize_profile_id(profile_id)
    session = StockSessionLocal()
    try:
        rows = session.execute(
            select(StockDocument).where(
                StockDocument.owner_id == owner_id,
                StockDocument.symbol == ticker,
                StockDocument.profile_id == profile,
                StockDocument.kind != NOTE_KIND,
            )
        ).scalars()
        return any(row.created_at and row.created_at > note_at for row in rows)
    finally:
        session.close()


def save_stock_note(owner_id: str, symbol: str, profile_id: str, title: str, envelope_json: str) -> None:
    ticker = normalize_symbol(symbol)
    if not ticker:
        return
    profile = normalize_profile_id(profile_id)
    session = StockSessionLocal()
    try:
        row = session.execute(
            select(StockDocument).where(
                StockDocument.owner_id == owner_id,
                StockDocument.symbol == ticker,
                StockDocument.profile_id == profile,
                StockDocument.kind == NOTE_KIND,
            )
        ).scalars().first()
        if row is None:
            session.add(
                StockDocument(
                    doc_id=new_doc_id(),
                    owner_id=owner_id,
                    symbol=ticker,
                    doc_title=title,
                    filename="note.json",
                    kind=NOTE_KIND,
                    body=envelope_json,
                    profile_id=profile,
                )
            )
        else:
            row.doc_title = title
            row.body = envelope_json
            row.created_at = datetime.utcnow()
        session.commit()
    finally:
        session.close()


def delete_user_document(doc_id: str, owner_id: str) -> bool:
    session = FinanceSessionLocal()
    try:
        row = session.get(UserDocument, doc_id)
        if row is not None and row.owner_id == owner_id:
            session.query(PolicyChunk).filter(PolicyChunk.doc_id == doc_id).delete(synchronize_session=False)
            session.delete(row)
            session.commit()
            user_pdf_path(owner_id, doc_id).unlink(missing_ok=True)
            return True
    finally:
        session.close()
    stock = StockSessionLocal()
    try:
        row = stock.get(StockDocument, doc_id)
        if row is None or row.owner_id != owner_id:
            return False
        stock.query(StockChunk).filter(StockChunk.doc_id == doc_id).delete(synchronize_session=False)
        stock.delete(row)
        stock.commit()
    finally:
        stock.close()
    stock_pdf_path(owner_id, doc_id).unlink(missing_ok=True)
    return True


def delete_profile_documents(owner_id: str, profile_id: str) -> None:
    profile = normalize_profile_id(profile_id)
    if profile == DEFAULT_PROFILE_ID:
        return
    finance = FinanceSessionLocal()
    try:
        docs = [
            row
            for row in _user_docs(finance, owner_id)
            if (row.profile_id or DEFAULT_PROFILE_ID) == profile
        ]
        for row in docs:
            finance.query(PolicyChunk).filter(PolicyChunk.doc_id == row.doc_id).delete(synchronize_session=False)
            finance.delete(row)
            user_pdf_path(owner_id, row.doc_id).unlink(missing_ok=True)
        finance.commit()
    finally:
        finance.close()
    stock = StockSessionLocal()
    try:
        docs = list(
            stock.execute(
                select(StockDocument).where(
                    StockDocument.owner_id == owner_id, StockDocument.profile_id == profile
                )
            ).scalars()
        )
        for row in docs:
            stock.query(StockChunk).filter(StockChunk.doc_id == row.doc_id).delete(synchronize_session=False)
            stock.delete(row)
            stock_pdf_path(owner_id, row.doc_id).unlink(missing_ok=True)
        stock.commit()
    finally:
        stock.close()


def chunk_count() -> int:
    session = FinanceSessionLocal()
    try:
        return session.query(PolicyChunk).count()
    finally:
        session.close()


def embedded_count() -> int:
    session = FinanceSessionLocal()
    try:
        rows = session.execute(select(PolicyChunk.embedding)).all()
        return sum(1 for (raw,) in rows if _vec(raw))
    finally:
        session.close()


def embed_missing_chunks() -> int:
    filled = 0
    for session_cls, model in ((FinanceSessionLocal, PolicyChunk), (StockSessionLocal, StockChunk)):
        session = session_cls()
        try:
            rows = [row for row in session.execute(select(model)).scalars() if not _vec(row.embedding)]
            if rows:
                filled += _attach_embeddings(rows)
                session.commit()
        finally:
            session.close()
    return filled
