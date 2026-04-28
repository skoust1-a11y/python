import pytest
from unittest.mock import patch, MagicMock
from app.db import db_operations

def test_insert_query_record_success():
    with patch("app.db.db_operations.SessionLocal") as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_record = MagicMock(id="uuid-test")
        with patch("app.db.db_operations.QueryRecord", return_value=mock_record):
            mock_session.add.return_value = None
            mock_session.commit.return_value = None
            mock_session.refresh.return_value = None
            result = db_operations.insert_query_record("query", "response")
            assert result == "uuid-test"
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_record)
            mock_session.close.assert_called_once()

def test_insert_query_record_db_error():
    with patch("app.db.db_operations.SessionLocal") as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.add.side_effect = Exception("DB error")
        with patch("app.db.db_operations.QueryRecord"):
            with pytest.raises(Exception):
                db_operations.insert_query_record("query", "response")
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
