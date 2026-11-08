"""Unit tests for the SQL query planner validation."""

import json

import pytest

from app.services.sql_query_planner import SqlQueryPlanner


@pytest.fixture
def planner() -> SqlQueryPlanner:
    return SqlQueryPlanner()


class TestSqlQueryPlannerValidation:
    def test_parses_hybrid_plan(self, planner: SqlQueryPlanner) -> None:
        raw = json.dumps(
            {
                "operations": [
                    {"type": "clauses_by_topic", "params": {"topic": "termination"}},
                    {"type": "case_by_number", "params": {"case_number": "XYZ-2024-001"}},
                ],
                "explanation": "Find termination clauses and related case",
            }
        )
        plan = planner._validate_plan(planner._parse_response(raw))
        assert len(plan.operations) == 2
        assert plan.operations[0].type == "clauses_by_topic"
        assert plan.operations[1].params["case_number"] == "XYZ-2024-001"

    def test_rejects_invalid_operation_type(self, planner: SqlQueryPlanner) -> None:
        raw = json.dumps(
            {
                "operations": [{"type": "raw_sql", "params": {"query": "SELECT 1"}}],
                "explanation": "bad",
            }
        )
        plan = planner._validate_plan(planner._parse_response(raw))
        assert plan.operations == ()

    def test_rejects_invalid_year(self, planner: SqlQueryPlanner) -> None:
        raw = json.dumps(
            {
                "operations": [{"type": "contracts_by_year", "params": {"year": 1800}}],
                "explanation": "bad year",
            }
        )
        plan = planner._validate_plan(planner._parse_response(raw))
        assert plan.operations == ()

    def test_metadata_lookup_requires_valid_uuid(self, planner: SqlQueryPlanner) -> None:
        raw = json.dumps(
            {
                "operations": [
                    {
                        "type": "metadata_lookup",
                        "params": {"entity_type": "document", "entity_id": "not-a-uuid"},
                    }
                ],
                "explanation": "bad id",
            }
        )
        plan = planner._validate_plan(planner._parse_response(raw))
        assert plan.operations == ()
