"""Generate C3 LegalDoc Navigator project presentation (.pptx)."""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# ── Brand palette ──────────────────────────────────────────────────────────
NAVY = RGBColor(0x1E, 0x3A, 0x5F)
TEAL = RGBColor(0x0D, 0x94, 0x88)
SLATE = RGBColor(0x64, 0x74, 0x8B)
DARK = RGBColor(0x1E, 0x29, 0x3B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG = RGBColor(0xF8, 0xFA, 0xFC)
ACCENT = RGBColor(0x03, 0x6B, 0x9A)
MUTED = RGBColor(0x94, 0xA3, 0xB8)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
MARGIN_L = Inches(0.65)
MARGIN_R = Inches(0.65)
CONTENT_W = SLIDE_W - MARGIN_L - MARGIN_R


def _set_font(run, *, size: int, bold: bool = False, color: RGBColor = DARK, name: str = "Calibri"):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _add_bg(slide, color: RGBColor = LIGHT_BG):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_header_bar(slide, title: str, slide_num: int | None = None):
    bar = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(0), SLIDE_W, Inches(1.05)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()

    accent = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(1.05), SLIDE_W, Inches(0.06)
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = TEAL
    accent.line.fill.background()

    box = slide.shapes.add_textbox(MARGIN_L, Inches(0.22), CONTENT_W, Inches(0.7))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title
    _set_font(run, size=28, bold=True, color=WHITE)

    if slide_num is not None:
        num_box = slide.shapes.add_textbox(Inches(12.2), Inches(0.3), Inches(0.8), Inches(0.4))
        p2 = num_box.text_frame.paragraphs[0]
        p2.alignment = PP_ALIGN.RIGHT
        r2 = p2.add_run()
        r2.text = str(slide_num)
        _set_font(r2, size=12, color=MUTED)


def _add_bullets(
    slide,
    items: list[str],
    *,
    left: float = 0.75,
    top: float = 1.45,
    width: float = 11.9,
    height: float = 5.5,
    size: int = 18,
    color: RGBColor = DARK,
):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(10)
        p.level = 0
        run = p.add_run()
        run.text = f"•  {item}"
        _set_font(run, size=size, color=color)


def _add_flow_boxes(
    slide,
    labels: list[str],
    *,
    top: float = 4.6,
    box_w: float = 1.45,
    box_h: float = 0.55,
    gap: float = 0.18,
    font_size: int = 11,
):
    total_w = len(labels) * box_w + (len(labels) - 1) * gap
    start_x = (13.333 - total_w) / 2
    x = start_x
    for i, label in enumerate(labels):
        shape = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(x),
            Inches(top),
            Inches(box_w),
            Inches(box_h),
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = ACCENT if i % 2 == 0 else TEAL
        shape.line.color.rgb = NAVY
        tf = shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = label
        _set_font(run, size=font_size, bold=True, color=WHITE)
        if i < len(labels) - 1:
            arrow = slide.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.RIGHT_ARROW,
                Inches(x + box_w + 0.02),
                Inches(top + 0.15),
                Inches(gap - 0.04),
                Inches(0.25),
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = SLATE
            arrow.line.fill.background()
        x += box_w + gap


def _add_architecture_diagram(slide):
    layers = [
        ("React + Vite UI", TEAL),
        ("FastAPI REST API", ACCENT),
        ("Services Layer", NAVY),
        ("RAG | SQL | Hybrid Pipelines", RGBColor(0x37, 0x5D, 0x8A)),
        ("OpenAI / Anthropic LLM", RGBColor(0x0F, 0x76, 0x6E)),
        ("PostgreSQL 16 + pgvector", RGBColor(0x33, 0x41, 0x55)),
    ]
    y = 1.55
    for label, color in layers:
        shape = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(3.8),
            Inches(y),
            Inches(5.7),
            Inches(0.62),
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.line.fill.background()
        tf = shape.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = label
        _set_font(run, size=15, bold=True, color=WHITE)
        if y < 5.5:
            arr = slide.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.DOWN_ARROW,
                Inches(6.35),
                Inches(y + 0.62),
                Inches(0.35),
                Inches(0.28),
            )
            arr.fill.solid()
            arr.fill.fore_color.rgb = SLATE
            arr.line.fill.background()
        y += 0.9

  # Side annotations
    side_items = [
        ("Langfuse", "Observability"),
        ("Guardrails AI", "Safety"),
        ("OCR Module", "Ingestion"),
        ("MCP (optional)", "External DBs"),
    ]
    sy = 2.0
    for title, sub in side_items:
        box = slide.shapes.add_textbox(Inches(0.75), Inches(sy), Inches(2.5), Inches(0.7))
        tf = box.text_frame
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = title
        _set_font(r1, size=13, bold=True, color=TEAL)
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = sub
        _set_font(r2, size=11, color=SLATE)
        sy += 1.1

    resp = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(10.2),
        Inches(5.8),
        Inches(2.4),
        Inches(0.62),
    )
    resp.fill.solid()
    resp.fill.fore_color.rgb = TEAL
    resp.line.fill.background()
    tf = resp.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = "Cited Response"
    _set_font(run, size=14, bold=True, color=WHITE)


def _add_tech_grid(slide):
    tech = [
        ("Frontend", "React 19, Vite, Tailwind CSS 4, TypeScript"),
        ("Backend", "Python 3.12, FastAPI, Uvicorn, Pydantic v2"),
        ("Database", "PostgreSQL 16 + pgvector (Qdrant optional)"),
        ("AI Framework", "LlamaIndex 0.12+"),
        ("Embeddings", "OpenAI text-embedding-3-small (1536-dim)"),
        ("LLM", "OpenAI (primary), Anthropic (fallback)"),
        ("Safety", "Guardrails AI + custom validators"),
        ("Monitoring", "Langfuse tracing (optional), RAGAS benchmarks"),
        ("OCR", "Scanned PDF text extraction (PyMuPDF + OCR)"),
        ("Deployment", "Docker Compose, Render, Vercel, Neon"),
    ]
    cols = 2
    col_w = 5.7
    row_h = 0.72
    start_y = 1.5
    for i, (label, value) in enumerate(tech):
        col = i % cols
        row = i // cols
        x = 0.75 + col * (col_w + 0.35)
        y = start_y + row * row_h
        card = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(x),
            Inches(y),
            Inches(col_w),
            Inches(row_h - 0.08),
        )
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
        tf = card.text_frame
        tf.margin_left = Inches(0.12)
        tf.margin_top = Inches(0.08)
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = label
        _set_font(r1, size=12, bold=True, color=TEAL)
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = value
        _set_font(r2, size=11, color=DARK)


def _add_feature_grid(slide, features: list[tuple[str, str]]):
    cols = 3
    col_w = 3.85
    row_h = 1.05
    start_y = 1.45
    for i, (title, desc) in enumerate(features):
        col = i % cols
        row = i // cols
        x = 0.65 + col * (col_w + 0.15)
        y = start_y + row * row_h
        card = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(x),
            Inches(y),
            Inches(col_w),
            Inches(row_h - 0.12),
        )
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
        tf = card.text_frame
        tf.margin_left = Inches(0.1)
        tf.margin_top = Inches(0.08)
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = title
        _set_font(r1, size=12, bold=True, color=NAVY)
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = desc
        _set_font(r2, size=10, color=SLATE)


def build_presentation() -> Presentation:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    # ── Slide 1: Title ─────────────────────────────────────────────────────
    s1 = prs.slides.add_slide(blank)
    _add_bg(s1, NAVY)
    accent_bar = s1.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(3.55), SLIDE_W, Inches(0.08)
    )
    accent_bar.fill.solid()
    accent_bar.fill.fore_color.rgb = TEAL
    accent_bar.line.fill.background()

    title_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.5), Inches(1.5))
    p = title_box.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = "C3 LegalDoc Navigator"
    _set_font(r, size=44, bold=True, color=WHITE)

    sub_box = s1.shapes.add_textbox(Inches(0.8), Inches(2.9), Inches(11.5), Inches(0.6))
    p2 = sub_box.text_frame.paragraphs[0]
    r2 = p2.add_run()
    r2.text = "AI-Powered Legal Document Analysis System"
    _set_font(r2, size=22, color=RGBColor(0xCB, 0xD5, 0xE1))

    meta_box = s1.shapes.add_textbox(Inches(0.8), Inches(4.2), Inches(11.5), Inches(2.0))
    tf = meta_box.text_frame
    for line in [
        "Team: C3 Team",
        "Guide: [Guide Name]",
        "Presenter: [Presenter Name]",
        "Date: July 7, 2026",
    ]:
        p = tf.paragraphs[0] if line == "Team: C3 Team" else tf.add_paragraph()
        p.space_after = Pt(6)
        run = p.add_run()
        run.text = line
        _set_font(run, size=16, color=RGBColor(0xE2, 0xE8, 0xF0))

    # ── Slide 2: Problem ───────────────────────────────────────────────────
    s2 = prs.slides.add_slide(blank)
    _add_bg(s2)
    _add_header_bar(s2, "Problem Statement", 2)
    _add_bullets(
        s2,
        [
            "Large volumes of contracts, agreements, and legal filings",
            "Manual keyword search misses semantic meaning",
            "Clause identification across documents is time-consuming",
            "Information scattered across multiple files and formats",
            "No unified Q&A over uploaded legal corpora",
            "Risk of misinterpreting obligations without source grounding",
        ],
        top=1.35,
        size=17,
    )
    _add_flow_boxes(
        s2,
        ["Upload Docs", "Manual Read", "Ctrl+F Search", "Slow Review", "Errors"],
        top=5.35,
        box_w=2.1,
        font_size=12,
    )

    # ── Slide 3: Solution ──────────────────────────────────────────────────
    s3 = prs.slides.add_slide(blank)
    _add_bg(s3)
    _add_header_bar(s3, "Proposed Solution", 3)
    _add_bullets(
        s3,
        [
            "AI-powered Legal Document Assistant with RAG",
            "Intelligent ingestion: PDF, DOCX, TXT + OCR for scanned PDFs",
            "Hybrid search: BM25 + semantic search via /search endpoint",
            "AI Q&A with intelligent routing (RAG, SQL, Hybrid)",
            "Three response modes: Strict, Explain, Analysis",
            "Source citations, confidence metrics, and guardrails",
            "Multi-document querying with optional document scope",
        ],
        top=1.3,
        width=6.2,
        size=15,
    )
    sol_box = s3.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(7.2), Inches(1.5), Inches(5.4), Inches(5.2)
    )
    sol_box.fill.solid()
    sol_box.fill.fore_color.rgb = WHITE
    sol_box.line.color.rgb = TEAL
    tf = sol_box.text_frame
    tf.margin_left = Inches(0.2)
    tf.margin_top = Inches(0.15)
    steps = [
        "USER",
        "  ↓",
        "Upload & Index",
        "  ↓",
        "Search / Chat",
        "  ↓",
        "Router → RAG | SQL | Hybrid",
        "  ↓",
        "Guardrails + Citations",
        "  ↓",
        "Grounded Answer",
    ]
    for i, step in enumerate(steps):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = step
        bold = step not in {"  ↓"}
        _set_font(run, size=13 if bold else 11, bold=bold, color=NAVY if bold else SLATE)

    # ── Slide 4: Architecture ──────────────────────────────────────────────
    s4 = prs.slides.add_slide(blank)
    _add_bg(s4)
    _add_header_bar(s4, "System Architecture", 4)
    _add_architecture_diagram(s4)

    # ── Slide 5: Tech Stack ────────────────────────────────────────────────
    s5 = prs.slides.add_slide(blank)
    _add_bg(s5)
    _add_header_bar(s5, "Technology Stack", 5)
    _add_tech_grid(s5)

    # ── Slide 6: Ingestion Pipeline ────────────────────────────────────────
    s6 = prs.slides.add_slide(blank)
    _add_bg(s6)
    _add_header_bar(s6, "Document Processing Pipeline", 6)
    _add_bullets(
        s6,
        [
            "Structure-aware chunking (tiktoken, 1024 tokens, 128 overlap)",
            "Metadata extraction: headings, clauses, sections, keywords",
            "OpenAI embeddings stored in pgvector (cosine similarity)",
            "Duplicate detection via content hash; multi-storage backends",
        ],
        top=1.3,
        height=2.0,
        size=15,
    )
    _add_flow_boxes(
        s6,
        ["Upload", "OCR*", "Parse", "Chunk", "Metadata", "Embed", "Store", "Ready"],
        top=4.0,
        box_w=1.35,
        font_size=10,
    )
    note = s6.shapes.add_textbox(Inches(0.75), Inches(5.0), Inches(11.5), Inches(0.5))
    p = note.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = "* OCR fallback for scanned PDFs via PyMuPDF page rendering (sequential, in-request)"
    _set_font(r, size=12, color=SLATE, bold=False)

    # ── Slide 7: Query Pipeline ────────────────────────────────────────────
    s7 = prs.slides.add_slide(blank)
    _add_bg(s7)
    _add_header_bar(s7, "Query Processing Pipeline (RAG)", 7)
    _add_flow_boxes(
        s7,
        ["Query", "Guardrails", "Router", "Retrieve", "Prompt", "LLM", "Validate", "Cite"],
        top=1.55,
        box_w=1.25,
        font_size=10,
    )
    _add_bullets(
        s7,
        [
            "LLM router classifies: RAG (dense vector) | SQL (structured) | Hybrid",
            "Hybrid: parallel vector + SQL + optional MCP → RRF fusion (k=60)",
            "PromptManager synthesizes Strict / Explain / Analysis responses",
            "Post-response guardrails + legal disclaimer + confidence scoring",
            "Separate /search endpoint: BM25 + semantic fusion (no LLM synthesis)",
        ],
        top=2.5,
        size=15,
    )

    # ── Slide 8: Key Features ──────────────────────────────────────────────
    s8 = prs.slides.add_slide(blank)
    _add_bg(s8)
    _add_header_bar(s8, "Key Features", 8)
    _add_feature_grid(
        s8,
        [
            ("AI Chat", "Natural-language Q&A with routing"),
            ("Document Search", "BM25 + semantic hybrid search"),
            ("Citations", "[Source N] grounding in answers"),
            ("Explain Mode", "Accessible default response"),
            ("Analysis Mode", "Structured claim evaluation"),
            ("Multi-Doc Query", "Optional document_id scope"),
            ("Confidence", "Retrieval + citation metrics"),
            ("Guardrails", "Pre/post safety validation"),
            ("Cost Tracking", "Per-request token cost (Langfuse)"),
            ("OCR Support", "Scanned PDF text extraction"),
            ("Human Handoff", "Low-confidence escalation"),
            ("Feedback", "User ratings (1–5)"),
        ],
    )

    # ── Slide 9: Technical Highlights ──────────────────────────────────────
    s9 = prs.slides.add_slide(blank)
    _add_bg(s9)
    _add_header_bar(s9, "Technical Highlights", 9)
    _add_bullets(
        s9,
        [
            "Clean layered architecture: Presentation → Application → Domain → Infrastructure",
            "FastAPI with dependency injection (app/dependencies.py)",
            "Modular services: QueryService, DocumentService, HandoffService",
            "LlamaIndex RAG pipeline with COMPACT synthesis mode",
            "PostgreSQL 16 + pgvector IVFFlat cosine search",
            "Hybrid retrieval with RRF, deduplication, keyword reranking",
            "Centralized PromptManager with three response modes",
            "Request logging middleware; per-query latency_ms in responses",
            "Offline RAGAS evaluation with CI benchmark gates",
            "Docker Compose + cloud deployment (Render, Vercel, Neon)",
        ],
        size=16,
    )

    # ── Slide 10: Evaluation Highlights ──────────────────────────────────
    s10 = prs.slides.add_slide(blank)
    _add_bg(s10)
    _add_header_bar(s10, "Evaluation-Oriented Technical Highlights", 10)
    eval_items = [
        ("✔", "Clean Layered Architecture", "Verified in codebase"),
        ("✔", "RAG + SQL + Hybrid Routing", "LLM classifier with fallback"),
        ("✔", "Reciprocal Rank Fusion (RRF)", "k=60 across retrieval paths"),
        ("✔", "Guardrails AI", "3 custom post-response validators"),
        ("✔", "Langfuse Observability", "Optional tracing + cost logging"),
        ("◐", "Cost Tracking", "Logged; budget limits not enforced"),
        ("✔", "Prompt Engineering", "Strict / Explain / Analysis modes"),
        ("◐", "OCR Support", "Scanned PDF fallback; sequential in-request"),
        ("✔", "Citation-Based Responses", "SourceCitation in API"),
        ("✔", "Explainable AI", "Analysis mode + MetricsEvaluator"),
        ("✔", "Modular / Extensible Design", "Parser factory, route registry"),
        ("◐", "Health Monitoring", "Static /health; DB check at startup"),
        ("✔", "Benchmarking", "RAGAS + golden dataset + CI gates"),
        ("✗", "Server Memory", "ChatHistory schema unused"),
        ("✗", "Authentication", "User model exists; no login API"),
    ]
    y = 1.4
    for sym, title, note in eval_items:
        row = s10.shapes.add_textbox(Inches(0.75), Inches(y), Inches(11.8), Inches(0.38))
        tf = row.text_frame
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = f"{sym}  {title}"
        color = TEAL if sym == "✔" else (RGBColor(0xD9, 0x77, 0x06) if sym == "◐" else RGBColor(0xDC, 0x26, 0x26))
        _set_font(r1, size=14, bold=True, color=color)
        r2 = p.add_run()
        r2.text = f"   —  {note}"
        _set_font(r2, size=12, color=SLATE)
        y += 0.36

    # ── Slide 11: Challenges ───────────────────────────────────────────────
    s11 = prs.slides.add_slide(blank)
    _add_bg(s11)
    _add_header_bar(s11, "Challenges Faced & Mitigations", 11)
    challenges = [
        ("OCR accuracy & speed", "PyMuPDF rendering + OCR fallback for scanned pages; sequential processing"),
        ("Chunking strategy", "Structure-aware LegalDocumentChunker with legal heading detection"),
        ("Retrieval quality", "Hybrid routing, RRF fusion, similarity threshold (0.7), keyword reranking"),
        ("Hallucination prevention", "Guardrails AI validators + citation-required checks + fallback responses"),
        ("Citation grounding", "Numbered [Source N] context blocks; SourceCitation in API responses"),
        ("Large documents", "Configurable chunk size/overlap; pgvector IVFFlat indexing"),
        ("Prompt engineering", "Three dedicated modes with PromptManager and analysis JSON parsing"),
    ]
    y = 1.4
    for challenge, mitigation in challenges:
        card = s11.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(0.75),
            Inches(y),
            Inches(11.8),
            Inches(0.72),
        )
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
        tf = card.text_frame
        tf.margin_left = Inches(0.15)
        tf.margin_top = Inches(0.1)
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = challenge
        _set_font(r1, size=13, bold=True, color=NAVY)
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = f"→ {mitigation}"
        _set_font(r2, size=11, color=SLATE)
        y += 0.82

    # ── Slide 12: Future Enhancements ────────────────────────────────────
    s12 = prs.slides.add_slide(blank)
    _add_bg(s12)
    _add_header_bar(s12, "Future Enhancements", 12)
    _add_bullets(
        s12,
        [
            "Server-side conversation memory (wire ChatHistory + session_id)",
            "BM25 fusion inside RAG /query pipeline (currently on /search only)",
            "Redis caching for repeated queries and BM25 corpus indexes",
            "Runtime budget enforcement with spend limits (HTTP 429)",
            "Prometheus /metrics endpoint and structured JSON logging",
            "Load testing with Locust/k6 scripts",
            "Deep health checks (DB, vector backend connectivity)",
            "pgvector HNSW indexes (replace IVFFlat)",
            "JWT authentication and role-based access control",
            "Background job queue for OCR and large-file ingestion",
        ],
        size=16,
    )

    # ── Slide 13: Demo ─────────────────────────────────────────────────────
    s13 = prs.slides.add_slide(blank)
    _add_bg(s13)
    _add_header_bar(s13, "Project Demonstration", 13)
    demo_steps = ["Upload", "Search", "Chat", "Explain", "Citations"]
    _add_flow_boxes(s13, demo_steps, top=1.4, box_w=2.1, font_size=13)

    placeholders = [
        ("Dashboard", "API status, document count, chunk stats"),
        ("Upload Page", "PDF/DOCX/TXT drag-and-drop indexing"),
        ("Search Page", "BM25 + semantic results with highlights"),
        ("Chat Page", "Q&A with mode toggles and source panel"),
        ("Citations Panel", "Source cards with chunk excerpts"),
        ("Analysis Metrics", "Faithfulness, relevance, confidence scores"),
    ]
    positions = [(0.75, 2.3), (4.55, 2.3), (8.35, 2.3), (0.75, 4.5), (4.55, 4.5), (8.35, 4.5)]
    for (title, desc), (x, y) in zip(placeholders, positions):
        ph = s13.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(x),
            Inches(y),
            Inches(3.5),
            Inches(1.9),
        )
        ph.fill.solid()
        ph.fill.fore_color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
        ph.line.color.rgb = SLATE
        tf = ph.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r1 = p.add_run()
        r1.text = f"[Screenshot: {title}]"
        _set_font(r1, size=12, bold=True, color=SLATE)
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run()
        r2.text = desc
        _set_font(r2, size=10, color=MUTED)

    # ── Slide 14: Conclusion ───────────────────────────────────────────────
    s14 = prs.slides.add_slide(blank)
    _add_bg(s14)
    _add_header_bar(s14, "Conclusion", 14)
    _add_bullets(
        s14,
        [
            "Problem: Legal document search and comprehension is manual, slow, and error-prone",
            "Solution: End-to-end AI assistant with ingestion, hybrid search, and grounded Q&A",
            "Benefits: Faster clause discovery, semantic understanding, cited answers",
            "Achievements: Production-grade RAG architecture with safety and observability hooks",
            "Impact: Reduces review time for contracts, NDAs, and compliance documents",
            "Maturity: Strong core pipeline; memory, auth, and ops metrics are planned next",
        ],
        size=18,
    )

    # ── Slide 15: Q&A ──────────────────────────────────────────────────────
    s15 = prs.slides.add_slide(blank)
    _add_bg(s15, NAVY)
    accent = s15.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(3.4), SLIDE_W, Inches(0.08)
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = TEAL
    accent.line.fill.background()

    q_box = s15.shapes.add_textbox(Inches(0), Inches(2.0), SLIDE_W, Inches(1.2))
    p = q_box.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "Questions?"
    _set_font(r, size=48, bold=True, color=WHITE)

    t_box = s15.shapes.add_textbox(Inches(0), Inches(4.0), SLIDE_W, Inches(1.0))
    p2 = t_box.text_frame.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = "Thank You"
    _set_font(r2, size=28, color=RGBColor(0xCB, 0xD5, 0xE1))

    c_box = s15.shapes.add_textbox(Inches(0), Inches(5.5), SLIDE_W, Inches(0.8))
    p3 = c_box.text_frame.paragraphs[0]
    p3.alignment = PP_ALIGN.CENTER
    r3 = p3.add_run()
    r3.text = "C3 LegalDoc Navigator  •  C3 Project  •  FastAPI + LlamaIndex + pgvector"
    _set_font(r3, size=14, color=MUTED)

    return prs


def main():
    out = Path(__file__).resolve().parent.parent / "docs" / "C3_LegalDoc_Navigator_Presentation.pptx"
    out.parent.mkdir(parents=True, exist_ok=True)
    prs = build_presentation()
    try:
        prs.save(str(out))
    except PermissionError:
        alt = out.with_name("C3_LegalDoc_Navigator_Presentation_updated.pptx")
        prs.save(str(alt))
        print(f"Original file is open — saved to: {alt}")
        return
    print(f"Presentation saved to: {out}")


if __name__ == "__main__":
    main()
