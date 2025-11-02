"""Unit tests for tools module."""

import json
import sqlite3
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch, create_autospec

import pytest

from react_agent.tools import (
    execute_sqlite_select,
    get_todays_date,
    inspect_sqlite_db,
)
import react_agent.tools as tools_module

# Helper function to create mock runtime
def create_mock_runtime(tool_call_id: str = "test-call-id"):
    """Create a mock ToolRuntime for testing."""
    mock_runtime = MagicMock()
    mock_runtime.tool_call_id = tool_call_id
    return mock_runtime


class TestGetTodaysDate:
    """Tests for get_todays_date tool."""

    def test_get_todays_date_returns_string(self) -> None:
        """Test that get_todays_date returns a string."""
        result = get_todays_date.invoke({})
        assert isinstance(result, str)

    def test_get_todays_date_format(self) -> None:
        """Test that get_todays_date returns YYYY-MM-DD format."""
        result = get_todays_date.invoke({})
        # Should match YYYY-MM-DD format
        assert len(result) == 10
        assert result[4] == "-"
        assert result[7] == "-"

    @patch("react_agent.tools.date")
    def test_get_todays_date_mocked(self, mock_date: MagicMock) -> None:
        """Test get_todays_date with mocked date."""
        mock_today = MagicMock()
        mock_today.strftime.return_value = "2025-08-14"
        mock_date.today.return_value = mock_today

        result = get_todays_date.invoke({})

        assert result == "2025-08-14"
        mock_today.strftime.assert_called_once_with("%Y-%m-%d")


class TestInspectSqliteDb:
    """Tests for inspect_sqlite_db tool."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary test database."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db") as f:
            db_path = Path(f.name)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create test tables
        cursor.execute(
            """
            CREATE TABLE budget_tracker (
                id INTEGER PRIMARY KEY,
                Date TEXT,
                Category TEXT,
                Expenditure REAL,
                Year INT,
                Month INT,
                Day INT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE budget_set (
                id INTEGER PRIMARY KEY,
                MonthYear TEXT,
                Category TEXT,
                Budget REAL
            )
        """
        )

        # Insert sample data
        cursor.execute(
            """
            INSERT INTO budget_tracker VALUES
            (1, '2024-01-15', 'Groceries', 100.50, 2024, 1, 15),
            (2, '2024-01-16', 'Transport', 50.00, 2024, 1, 16)
        """
        )

        cursor.execute(
            """
            INSERT INTO budget_set VALUES
            (1, 'Jan 2024', 'Groceries', 500.00)
        """
        )

        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        db_path.unlink()

    def test_inspect_sqlite_db_structure(self, temp_db: Path) -> None:
        """Test that inspect_sqlite_db returns proper structure."""
        # Mock the db_path in the tool
        with patch.object(tools_module, 'sqlite3') as mock_sqlite:
            mock_sqlite.connect.return_value = sqlite3.connect(temp_db)
            mock_sqlite.Row = sqlite3.Row
            mock_sqlite.Error = sqlite3.Error

            result = inspect_sqlite_db.invoke({})
            data = json.loads(result)

            assert isinstance(data, dict)
            assert "budget_tracker" in data
            assert "budget_set" in data
            assert "schema" in data["budget_tracker"]
            assert "sample_rows" in data["budget_tracker"]

    def test_inspect_sqlite_db_sample_rows_limit(self, temp_db: Path) -> None:
        """Test that inspect_sqlite_db returns max 5 sample rows."""
        with patch.object(tools_module, 'sqlite3') as mock_sqlite:
            mock_sqlite.connect.return_value = sqlite3.connect(temp_db)
            mock_sqlite.Row = sqlite3.Row
            mock_sqlite.Error = sqlite3.Error

            result = inspect_sqlite_db.invoke({})
            data = json.loads(result)

            # Should return at most 5 rows
            assert len(data["budget_tracker"]["sample_rows"]) <= 5
            assert len(data["budget_set"]["sample_rows"]) <= 5

    @patch("react_agent.tools.sqlite3.connect")
    def test_inspect_sqlite_db_error_handling(self, mock_connect: MagicMock) -> None:
        """Test that inspect_sqlite_db handles database errors."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("Database error")

        result = inspect_sqlite_db.invoke({})
        data = json.loads(result)

        assert "error" in data
        assert "Database error" in data["error"]


class TestExecuteSqliteSelect:
    """Tests for execute_sqlite_select tool."""

    @pytest.fixture(autouse=True)
    def reset_query_list(self) -> None:
        """Reset the global query_list before each test."""
        tools_module.query_list.clear()

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary test database."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db") as f:
            db_path = Path(f.name)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE budget_tracker (
                id INTEGER PRIMARY KEY,
                Category TEXT,
                Expenditure REAL
            )
        """
        )

        cursor.execute(
            """
            INSERT INTO budget_tracker VALUES
            (1, 'Groceries', 100.50),
            (2, 'Transport', 50.00)
        """
        )

        conn.commit()
        conn.close()

        yield db_path
        db_path.unlink()

    def test_execute_sqlite_select_valid_query(self, temp_db: Path) -> None:
        """Test executing a valid SELECT query."""
        with patch.object(tools_module, 'sqlite3') as mock_sqlite:
            mock_sqlite.connect.return_value = sqlite3.connect(temp_db)
            mock_sqlite.Error = sqlite3.Error

            runtime = create_mock_runtime()

            # Call the function directly instead of through invoke
            result = execute_sqlite_select.func(
                query="SELECT * FROM budget_tracker", runtime=runtime
            )

            assert hasattr(result, "update")
            assert "messages" in result.update
            assert "query" in result.update

    def test_execute_sqlite_select_rejects_non_select(self) -> None:
        """Test that non-SELECT queries are rejected."""
        runtime = create_mock_runtime()

        # Call the function directly
        result = execute_sqlite_select.func(
            query="DELETE FROM budget_tracker", runtime=runtime
        )

        assert hasattr(result, "update")
        assert "Only SELECT queries are allowed" in str(result.update["messages"][0].content)

    def test_execute_sqlite_select_rejects_insert(self) -> None:
        """Test that INSERT queries are rejected."""
        runtime = create_mock_runtime()

        result = execute_sqlite_select.func(
            query="INSERT INTO budget_tracker VALUES (3, 'Food', 75.00)",
            runtime=runtime,
        )

        assert "Only SELECT queries are allowed" in str(result.update["messages"][0].content)

    def test_execute_sqlite_select_rejects_update(self) -> None:
        """Test that UPDATE queries are rejected."""
        runtime = create_mock_runtime()

        result = execute_sqlite_select.func(
            query="UPDATE budget_tracker SET Expenditure = 0", runtime=runtime
        )

        assert "Only SELECT queries are allowed" in str(result.update["messages"][0].content)

    def test_execute_sqlite_select_rejects_drop(self) -> None:
        """Test that DROP queries are rejected."""
        runtime = create_mock_runtime()

        result = execute_sqlite_select.func(
            query="DROP TABLE budget_tracker", runtime=runtime
        )

        assert "Only SELECT queries are allowed" in str(result.update["messages"][0].content)

    def test_execute_sqlite_select_tracks_queries(self, temp_db: Path) -> None:
        """Test that executed queries are tracked in state."""
        with patch.object(tools_module, 'sqlite3') as mock_sqlite:
            mock_sqlite.connect.return_value = sqlite3.connect(temp_db)
            mock_sqlite.Error = sqlite3.Error

            runtime = create_mock_runtime()

            query = "SELECT * FROM budget_tracker WHERE Category = 'Groceries'"
            result = execute_sqlite_select.func(query=query, runtime=runtime)

            # Query should be added to the query list
            assert query in result.update["query"]

    def test_execute_sqlite_select_handles_errors(self) -> None:
        """Test that database errors are handled gracefully."""
        with patch.object(tools_module, 'sqlite3') as mock_sqlite:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_sqlite.connect.return_value = mock_conn
            mock_sqlite.Error = sqlite3.Error
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = sqlite3.Error("Syntax error")

            runtime = create_mock_runtime()

            result = execute_sqlite_select.func(
                query="SELECT * FROM nonexistent", runtime=runtime
            )

            assert "Error executing query" in str(result.update["messages"][0].content)

    def test_execute_sqlite_select_returns_dict_results(self, temp_db: Path) -> None:
        """Test that results are returned as list of dicts."""
        with patch.object(tools_module, 'sqlite3') as mock_sqlite:
            mock_sqlite.connect.return_value = sqlite3.connect(temp_db)
            mock_sqlite.Error = sqlite3.Error

            runtime = create_mock_runtime()

            result = execute_sqlite_select.func(
                query="SELECT * FROM budget_tracker LIMIT 1", runtime=runtime
            )

            message_content = str(result.update["messages"][0].content)
            # Should contain dict-like structure with column names
            assert "Category" in message_content or "Expenditure" in message_content
