"""Tests for pipeline-level evidence validation integration."""

from app.utils.evidence_validator import filter_public_sources


def test_public_sources_kept_when_evidence_insufficient():
  """Regression: sources must remain for guardrails and UI when validation fails."""
  sources = [{"score": 0.9, "full_text": "Sample clause.", "excerpt": "Sample clause."}]
  assert filter_public_sources(sources, evidence_sufficient=False) == sources


def test_public_sources_returned_when_evidence_sufficient():
  sources = [{"score": 0.9, "full_text": "Sample clause.", "excerpt": "Sample clause."}]
  assert filter_public_sources(sources, evidence_sufficient=True) == sources
