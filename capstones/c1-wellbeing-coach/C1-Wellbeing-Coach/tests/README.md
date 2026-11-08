"""Tests directory for Wellbeing Coach application.

Test Structure:
===============

tests/
├── conftest.py                      # Pytest fixtures and configuration
├── unit/                            # Unit tests
│   ├── test_models.py              # Data model validation tests
│   └── test_services.py            # Service layer tests (MemoryService, etc.)
└── integration/                     # Integration tests
    ├── test_feedback_routes.py      # Feedback API endpoint tests
    └── test_wellbeing_routes.py     # Wellbeing API endpoint tests

Running Tests:
==============

# Install test dependencies
pip install -r requirements-test.txt
# or
uv pip install -r requirements-test.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only unit tests
pytest tests/unit -v

# Run only integration tests
pytest tests/integration -v

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py -v

# Run specific test class
pytest tests/unit/test_models.py::TestFeedbackModel -v

# Run specific test function
pytest tests/unit/test_models.py::TestFeedbackModel::test_feedback_with_rating_only -v

Test Categories:
================

UNIT TESTS (tests/unit/):
- test_models.py: Tests for Pydantic data models
  * Feedback model validation
  * Optional field handling
  * Data type validation
  
- test_services.py: Tests for business logic services
  * MemoryService.store_interaction()
  * MemoryService.get_history()
  * MemoryService.update_feedback()
  * MemoryService.has_feedback()
  * Error handling and validation

INTEGRATION TESTS (tests/integration/):
- test_feedback_routes.py: Tests for feedback API endpoints
  * POST /feedback/store with various input combinations
  * Rating and comment validation
  * Database persistence
  * Error responses
  
- test_wellbeing_routes.py: Tests for wellbeing API endpoints
  * POST /wellbeing/analyze emotion analysis
  * GET /wellbeing/history user interaction history
  * Data storage and retrieval
  * User separation and history ordering

Fixtures (conftest.py):
=======================

- test_db: Provides test database with schema
- db_session: Fresh database session for each test
- client: FastAPI TestClient for API testing
- clear_db: Automatically clears database between tests
- sample_interaction_data: Sample interaction for testing
- sample_feedback_data: Sample feedback for testing

Coverage Goals:
===============

- Models: 100% (validation, types)
- Services: 95%+ (business logic, error cases)
- Routes: 90%+ (API contracts, status codes, error responses)

Key Test Scenarios:
===================

Feedback Tests:
✓ Rating only (no comment)
✓ Comment only (no rating)
✓ Both rating and comment
✓ Neither (should fail)
✓ Invalid rating ranges (0, 6+)
✓ Long comments (>500 chars)
✓ Non-existent interactions
✓ Multiple updates
✓ Database persistence

Wellbeing Tests:
✓ Emotion analysis with valid input
✓ Missing required fields
✓ Multiple interactions per user
✓ User history retrieval
✓ History ordering (most recent first)
✓ History limit (50 entries)
✓ User data separation

Notes:
======

- Tests use a separate test database to avoid affecting production data
- Database is created fresh for each test session
- Each test function gets a clean database state
- Fixtures handle setup and teardown automatically
- Use pytest markers for categorizing tests (@pytest.mark.unit, @pytest.mark.integration)
"""
