"""Unit tests for graph module."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from react_agent.graph import route_model_output
from react_agent.state import State


class TestRouteModelOutput:
    """Tests for route_model_output function."""

    def test_route_model_output_ends_when_no_tool_calls(self) -> None:
        """Test that routing ends when AIMessage has no tool calls."""
        state = State(
            messages=[
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!"),
            ]
        )

        result = route_model_output(state)

        assert result == "__end__"

    def test_route_model_output_continues_to_tools_when_tool_calls_present(self) -> None:
        """Test that routing goes to tools when AIMessage has tool calls."""
        state = State(
            messages=[
                HumanMessage(content="What's the date?"),
                AIMessage(
                    content="Let me check",
                    tool_calls=[
                        {
                            "name": "get_todays_date",
                            "args": {},
                            "id": "call_1",
                        }
                    ],
                ),
            ]
        )

        result = route_model_output(state)

        assert result == "tools"

    def test_route_model_output_with_multiple_tool_calls(self) -> None:
        """Test routing with multiple tool calls."""
        state = State(
            messages=[
                HumanMessage(content="Check database and get date"),
                AIMessage(
                    content="I'll check both",
                    tool_calls=[
                        {"name": "get_todays_date", "args": {}, "id": "call_1"},
                        {"name": "inspect_sqlite_db", "args": {}, "id": "call_2"},
                    ],
                ),
            ]
        )

        result = route_model_output(state)

        assert result == "tools"

    def test_route_model_output_after_tool_execution(self) -> None:
        """Test routing after tool execution completes."""
        state = State(
            messages=[
                HumanMessage(content="What's the date?"),
                AIMessage(
                    content="Let me check",
                    tool_calls=[{"name": "get_todays_date", "args": {}, "id": "call_1"}],
                ),
                ToolMessage(content="2025-08-14", tool_call_id="call_1"),
                AIMessage(content="Today's date is 2025-08-14"),
            ]
        )

        result = route_model_output(state)

        # Should end since last message has no tool calls
        assert result == "__end__"

    def test_route_model_output_with_empty_tool_calls_list(self) -> None:
        """Test routing when tool_calls is empty list."""
        state = State(
            messages=[
                HumanMessage(content="Hello"),
                AIMessage(content="Hi!", tool_calls=[]),
            ]
        )

        result = route_model_output(state)

        assert result == "__end__"

    def test_route_model_output_raises_error_for_non_ai_message(self) -> None:
        """Test that routing raises error when last message is not AIMessage."""
        state = State(messages=[HumanMessage(content="Hello")])

        with pytest.raises(ValueError, match="Expected AIMessage"):
            route_model_output(state)

    def test_route_model_output_raises_error_for_tool_message(self) -> None:
        """Test that routing raises error when last message is ToolMessage."""
        state = State(
            messages=[
                HumanMessage(content="Test"),
                AIMessage(
                    content="Checking",
                    tool_calls=[{"name": "get_todays_date", "args": {}, "id": "call_1"}],
                ),
                ToolMessage(content="2025-08-14", tool_call_id="call_1"),
            ]
        )

        with pytest.raises(ValueError, match="Expected AIMessage"):
            route_model_output(state)

    def test_route_model_output_with_sql_query_tool_call(self) -> None:
        """Test routing with execute_sqlite_select tool call."""
        state = State(
            messages=[
                HumanMessage(content="How much did I spend on groceries?"),
                AIMessage(
                    content="Let me query the database",
                    tool_calls=[
                        {
                            "name": "execute_sqlite_select",
                            "args": {
                                "query": "SELECT SUM(Expenditure) FROM budget_tracker WHERE Category='Groceries'"
                            },
                            "id": "call_1",
                        }
                    ],
                ),
            ]
        )

        result = route_model_output(state)

        assert result == "tools"

    def test_route_model_output_conversation_flow(self) -> None:
        """Test routing through a complete conversation flow."""
        # First routing - should go to tools
        state1 = State(
            messages=[
                HumanMessage(content="What's the date?"),
                AIMessage(
                    content="Checking...",
                    tool_calls=[{"name": "get_todays_date", "args": {}, "id": "call_1"}],
                ),
            ]
        )
        assert route_model_output(state1) == "tools"

        # After tool execution - should end
        state2 = State(
            messages=[
                HumanMessage(content="What's the date?"),
                AIMessage(
                    content="Checking...",
                    tool_calls=[{"name": "get_todays_date", "args": {}, "id": "call_1"}],
                ),
                ToolMessage(content="2025-08-14", tool_call_id="call_1"),
                AIMessage(content="Today is 2025-08-14"),
            ]
        )
        assert route_model_output(state2) == "__end__"

    def test_route_model_output_with_inspect_db_tool(self) -> None:
        """Test routing with inspect_sqlite_db tool call."""
        state = State(
            messages=[
                HumanMessage(content="Show me the database structure"),
                AIMessage(
                    content="Let me inspect the database",
                    tool_calls=[
                        {"name": "inspect_sqlite_db", "args": {}, "id": "call_1"}
                    ],
                ),
            ]
        )

        result = route_model_output(state)

        assert result == "tools"

    def test_route_model_output_with_none_tool_calls(self) -> None:
        """Test routing when tool_calls attribute doesn't exist or is None."""
        # Create AIMessage without tool_calls
        ai_msg = AIMessage(content="Just a response")
        # Ensure tool_calls is empty list (default behavior)
        assert ai_msg.tool_calls == []

        state = State(messages=[HumanMessage(content="Hi"), ai_msg])

        result = route_model_output(state)

        assert result == "__end__"
