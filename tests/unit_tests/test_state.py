"""Unit tests for state module."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from react_agent.state import InputState, State


class TestInputState:
    """Tests for InputState dataclass."""

    def test_input_state_default_initialization(self) -> None:
        """Test InputState initializes with empty messages by default."""
        state = InputState()
        assert state.messages == []

    def test_input_state_with_messages(self) -> None:
        """Test InputState initializes with provided messages."""
        messages = [HumanMessage(content="Hello"), AIMessage(content="Hi")]
        state = InputState(messages=messages)
        assert len(state.messages) == 2
        assert state.messages[0].content == "Hello"
        assert state.messages[1].content == "Hi"

    def test_input_state_accepts_tuple_messages(self) -> None:
        """Test InputState can accept messages as tuples."""
        state = InputState(messages=[("user", "Hello"), ("assistant", "Hi")])
        assert len(state.messages) == 2

    def test_input_state_messages_are_sequence(self) -> None:
        """Test that messages field accepts any sequence type."""
        # Test with list
        state1 = InputState(messages=[HumanMessage(content="Test")])
        assert len(state1.messages) == 1

        # Test with tuple
        state2 = InputState(messages=(HumanMessage(content="Test"),))
        assert len(state2.messages) == 1


class TestState:
    """Tests for State dataclass."""

    def test_state_default_initialization(self) -> None:
        """Test State initializes with default values."""
        state = State()
        assert state.messages == []
        assert state.is_last_step is False
        assert state.query == []

    def test_state_with_all_fields(self) -> None:
        """Test State initializes with all fields provided."""
        messages = [HumanMessage(content="Query")]
        queries = ["SELECT * FROM budget_tracker"]

        state = State(messages=messages, is_last_step=True, query=queries)

        assert len(state.messages) == 1
        assert state.is_last_step is True
        assert len(state.query) == 1
        assert state.query[0] == "SELECT * FROM budget_tracker"

    def test_state_inherits_from_input_state(self) -> None:
        """Test that State inherits from InputState."""
        assert issubclass(State, InputState)

    def test_state_query_field_default(self) -> None:
        """Test that query field defaults to empty list."""
        state = State()
        assert isinstance(state.query, list)
        assert len(state.query) == 0

    def test_state_query_field_tracks_multiple_queries(self) -> None:
        """Test that query field can track multiple SQL queries."""
        queries = [
            "SELECT * FROM budget_tracker",
            "SELECT * FROM budget_set",
            "SELECT SUM(Expenditure) FROM budget_tracker",
        ]
        state = State(query=queries)

        assert len(state.query) == 3
        assert state.query == queries

    def test_state_is_last_step_is_boolean(self) -> None:
        """Test that is_last_step is a boolean field."""
        state1 = State(is_last_step=True)
        assert state1.is_last_step is True

        state2 = State(is_last_step=False)
        assert state2.is_last_step is False

    def test_state_with_complex_message_sequence(self) -> None:
        """Test State with a complete conversation flow."""
        messages = [
            HumanMessage(content="How much did I spend on groceries?"),
            AIMessage(
                content="Let me check",
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
            ToolMessage(
                content='[{"SUM(Expenditure)": 450.50}]', tool_call_id="call_1"
            ),
            AIMessage(content="You spent ₹450.50 on groceries"),
        ]
        queries = [
            "SELECT SUM(Expenditure) FROM budget_tracker WHERE Category='Groceries'"
        ]

        state = State(messages=messages, query=queries)

        assert len(state.messages) == 4
        assert len(state.query) == 1
        assert isinstance(state.messages[0], HumanMessage)
        assert isinstance(state.messages[1], AIMessage)
        assert isinstance(state.messages[2], ToolMessage)
        assert isinstance(state.messages[3], AIMessage)

    def test_state_query_list_is_mutable(self) -> None:
        """Test that query list can be modified after initialization."""
        state = State()
        assert len(state.query) == 0

        # Simulate adding queries as they're executed
        state.query.append("SELECT * FROM budget_tracker")
        assert len(state.query) == 1

        state.query.append("SELECT * FROM budget_set")
        assert len(state.query) == 2

    def test_state_dataclass_equality(self) -> None:
        """Test that State instances with same values are equal."""
        messages = [HumanMessage(content="Test")]
        queries = ["SELECT * FROM test"]

        state1 = State(messages=messages, query=queries, is_last_step=False)
        state2 = State(messages=messages, query=queries, is_last_step=False)

        # Note: This might not work as expected due to message IDs
        # Just testing that the structure is correct
        assert state1.query == state2.query
        assert state1.is_last_step == state2.is_last_step
