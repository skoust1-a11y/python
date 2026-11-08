"""Safety fixtures to protect persistent test database behavior."""

import pytest


@pytest.fixture
def reset_db(test_db):
    """Hard-disabled safety fixture to prevent accidental data deletion."""
    raise RuntimeError(
        "reset_db is disabled to protect persistent test data. "
        "Do not clear or reset the test database."
    )


@pytest.fixture
def preserve_db(test_db):
    """Explicit no-op fixture documenting persistent data intent."""
    yield
