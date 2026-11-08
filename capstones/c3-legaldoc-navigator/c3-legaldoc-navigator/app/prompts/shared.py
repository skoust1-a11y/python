"""Shared prompt fragments reused across response modes.

Centralising citation rules and legal constraints here keeps mode-specific
prompts focused on behaviour differences and avoids duplicated instructions
that would drift out of sync during maintenance.
"""

# Citation format used in all modes that reference retrieved chunks.
CITATION_RULES = """## Citation rules

- Use only [Source N] labels that appear in the provided context blocks.
- Place each citation immediately after the clause or claim it supports.
- Do not cite a source for text absent from that source's block.
"""

# Evidence mode must never cross the line into synthesis.
EVIDENCE_EXTRACTION_RULES = """## Evidence extraction rules (mandatory)

- Extract clause text verbatim or with minimal trimming — never paraphrase into an answer.
- Include EVERY directly relevant clause (text that explicitly addresses the question topic).
- Include EVERY indirectly relevant clause (text needed to answer scenario or calculation questions,
  e.g. payment terms + GST rate + late-fee provisions for a cost scenario).
- Multiple clauses may collectively support an answer — return all of them.
- Do NOT answer the user's question.
- Do NOT perform reasoning, inference, calculations, or synthesis.
- Do NOT state conclusions (e.g. do not compute totals or predict outcomes).
- Do NOT use outside knowledge or assumptions.
"""

# When no clause in the retrieved context relates to the question topic.
EVIDENCE_NONE_FOUND_RESPONSE = "No relevant clauses found in the retrieved context."
