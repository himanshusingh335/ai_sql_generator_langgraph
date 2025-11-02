# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI SQL Generator built with LangGraph - a ReAct agent that converts natural language questions about budget data into SQL queries, executes them against a SQLite database, and presents results as formatted financial insights.

The agent uses a Reasoning and Action (ReAct) pattern where it iteratively:
1. Reasons about user budget questions
2. Inspects database schema (if needed)
3. Generates and executes SQL queries
4. Formats results with currency and financial context
5. Provides actionable insights

**Key specialty**: The agent is specifically designed for budget analysis, working with a SQLite database at `data/budget.db` containing two tables:
- `budget_tracker`: Expenditure records with Date (text), Year/Month/Day (integers), Category, Expenditure amount
- `budget_set`: Monthly budget allocations by Category

## Development Commands

### Python Environment
The project uses Python 3.11+ and has a dedicated virtual environment `ai_sql_generator_env`. Activate it before running commands:
```bash
source ai_sql_generator_env/bin/activate
```

### Running Tests
```bash
# Run all tests (55 total: 54 unit + 1 integration)
pytest tests/ -v

# Run ONLY unit tests (fast, no API calls needed)
pytest tests/unit_tests/ -v
# 54 tests covering: utils, tools, state, graph routing

# Run ONLY integration test (requires API key or VCR cassette)
pytest tests/integration_tests/ -v
# 1 end-to-end test

# Useful test flags
pytest tests/unit_tests/ -v --tb=short  # Shorter tracebacks
pytest tests/unit_tests/ -x             # Stop at first failure
pytest tests/unit_tests/ -k "select"    # Run tests matching pattern
pytest tests/unit_tests/ --lf           # Run last failed
```

### Linting and Type Checking
```bash
# Run ruff linter
ruff check .

# Run mypy type checker
mypy src/
```

### LangGraph Studio
Open this directory in LangGraph Studio to visualize and debug the agent graph interactively. The graph is defined in `langgraph.json` and points to `src/react_agent/graph.py:graph`.

### Running the Agent
The agent is designed to run via LangGraph Studio or deployed as a LangGraph service. For programmatic use:
```python
from react_agent import graph
from react_agent.context import Context

result = await graph.ainvoke(
    {"messages": [("user", "How much did we spend on groceries last month?")]},
    context=Context(model="openai/gpt-4o-mini")
)
```

## Architecture

### Core Components

**State Management** ([state.py](src/react_agent/state.py:1))
- `InputState`: Messages sequence with `add_messages` reducer
- `State`: Extends InputState with:
  - `is_last_step`: Managed variable preventing infinite loops
  - `query`: List tracking executed SQL queries during conversation

**Graph Structure** ([graph.py](src/react_agent/graph.py:1))
- Entry: `call_model` node invokes LLM with tool binding
- Conditional routing: If AI returns tool calls → `tools` node, else → end
- Cycle: `tools` → `call_model` (continues until final answer)
- The graph uses LangGraph's `StateGraph` with `Runtime[Context]` for configuration

**Tools** ([tools.py](src/react_agent/tools.py:1))
Three specialized tools:
1. `get_todays_date()`: Returns current date in YYYY-MM-DD format
2. `inspect_sqlite_db()`: Returns complete schema + 5 sample rows per table as JSON
3. `execute_sqlite_select(query, runtime)`: Executes SELECT queries only, returns `Command` with state updates including query history

**Important**:
- `execute_sqlite_select` uses `Command` pattern to update both the `query` list and messages, ensuring state synchronization
- It enforces SELECT-only for safety - rejects DELETE, INSERT, UPDATE, DROP queries
- Global `query_list` variable tracks all executed queries (must be reset in tests)
- Requires `ToolRuntime` parameter with `tool_call_id` attribute

**Context & Configuration** ([context.py](src/react_agent/context.py:1))
- `Context` dataclass defines runtime parameters:
  - `system_prompt`: Defaults to budget analysis prompt
  - `model`: Format is `provider/model-name` (e.g., "openai/gpt-4o-mini")
  - `max_search_results`: Not actively used by SQL tools
- Model loading via `load_chat_model(fully_specified_name)` uses LangChain's `init_chat_model`

**System Prompt** ([prompts.py](src/react_agent/prompts.py:1))
The agent is instructed to:
- Always use structured date fields (Year, Month, Day) over text Date field
- Execute multiple queries for complex questions
- Format results with ₹ currency symbol
- Provide financial insights and actionable context
- Show executed SQL queries for transparency

### Key Design Patterns

**Structured Data Preference**: The prompt explicitly instructs to use `Year`, `Month`, `Day` integer columns instead of parsing the text `Date` field. This is crucial for reliable date filtering and grouping.

**Tool-Result-Action Cycle**: Messages accumulate as: HumanMessage → AIMessage (with tool_calls) → ToolMessage(s) → AIMessage (final answer). The `add_messages` reducer merges by ID.

**Command Pattern for State Updates**: Unlike simple tool returns, `execute_sqlite_select` returns a `Command(update={...})` to modify multiple state fields atomically (both `query` list and `messages`).

**Recursion Limit Protection**: The `is_last_step` managed variable triggers when approaching recursion limit, forcing the agent to return an error message instead of attempting more tool calls.

## Project Structure

```
src/react_agent/
├── __init__.py          # Exports graph
├── graph.py             # StateGraph definition, call_model node, routing logic
├── state.py             # InputState and State dataclasses
├── tools.py             # Three tools: date, inspect_db, execute_select
├── context.py           # Context configuration dataclass
├── prompts.py           # SYSTEM_PROMPT for budget analysis
└── utils.py             # load_chat_model, get_message_text helpers

tests/
├── conftest.py          # Pytest configuration
├── unit_tests/          # Unit tests for components
└── integration_tests/   # End-to-end graph tests with VCR cassettes

data/
└── budget.db            # SQLite database (not in version control)
```

## Environment Setup

Required environment variables (see [.env.example](.env.example:1)):
- One of: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `FIREWORKS_API_KEY`
- `TAVILY_API_KEY` (not actively used by current tools, but included in template)
- Optional: `LANGSMITH_PROJECT` for tracing

## Database Schema Reference

**budget_tracker**
- Stores individual expenditure records
- Columns: id, Date (text), Description, Category, Expenditure (amount), Year, Month, Day
- Use Year/Month/Day for all date operations

**budget_set**
- Stores monthly budget allocations
- Columns: id, MonthYear (text like "Jan 2024"), Category, Budget (amount)
- Join with budget_tracker on Category to compare actual vs budget

## Testing Architecture

### Unit Tests (54 tests)
Comprehensive coverage of individual components without external dependencies:

**[test_utils.py](tests/unit_tests/test_utils.py:1)** - 13 tests
- `get_message_text()`: Handles string, list, dict content formats
- `load_chat_model()`: Model loading for OpenAI, Anthropic, Fireworks

**[test_tools.py](tests/unit_tests/test_tools.py:1)** - 14 tests
- `get_todays_date()`: Date formatting and mocking
- `inspect_sqlite_db()`: Schema inspection with temp databases
- `execute_sqlite_select()`: Query validation, SQL injection prevention (DELETE/INSERT/UPDATE/DROP rejection), error handling, state tracking

**[test_state.py](tests/unit_tests/test_state.py:1)** - 13 tests
- `InputState` and `State` initialization, field validation, message handling

**[test_graph.py](tests/unit_tests/test_graph.py:1)** - 11 tests
- `route_model_output()`: Routing logic, tool call detection, error cases

**[test_configuration.py](tests/unit_tests/test_configuration.py:1)** - 3 tests
- `Context` initialization and environment variable handling

### Integration Tests (1 test)
**[test_graph.py](tests/integration_tests/test_graph.py:1)** - End-to-end test
- Uses `pytest-vcr` to record/replay LLM interactions as YAML cassettes in `tests/cassettes/`
- Requires `pytest-anyio` for async support
- Demonstrates full graph execution with custom Context

### Testing Best Practices
- **Global state**: Tests use `autouse` fixtures to reset `query_list` between tests
- **Database tests**: Use temporary databases created in fixtures, cleaned up after tests
- **Tool testing**: Call `.func()` directly instead of `.invoke()` to bypass Pydantic validation complexity
- **Mocking**: Use `MagicMock` for ToolRuntime, patch sqlite3 module for database tests
- **Message content**: AIMessage content must be string or list, not plain dict

## Important Conventions

1. **Model specification**: Always use `provider/model-name` format (e.g., "anthropic/claude-3-5-sonnet-20241022", "openai/gpt-4o")
2. **Date handling**: Prefer structured integer columns (Year, Month, Day) over text Date parsing
3. **Currency formatting**: Use ₹ symbol in responses
4. **Query transparency**: Always show executed SQL in final responses
5. **Safety**: Only SELECT queries allowed via `execute_sqlite_select` tool
6. **State updates**: Use `Command` pattern when tools need to update multiple state fields

## Common Development Pitfalls

### Testing
- Don't forget to reset global `query_list` between tests (use `autouse` fixture)
- Test tools via `.func()` method, not `.invoke()` to avoid Pydantic validation issues
- AIMessage content cannot be a plain dict - must be string or list
- When mocking sqlite3, also mock `sqlite3.Row` and `sqlite3.Error`

### Tool Development
- Tools that modify state must return `Command(update={...})` not plain values
- ToolRuntime cannot be easily mocked - create mock object with `tool_call_id` attribute
- Database path in `inspect_sqlite_db` is hardcoded to `data/budget.db`

### Message Handling
- `get_message_text()` handles multiple content formats - check implementation before assuming structure
- The `add_messages` reducer merges messages by ID, not appending duplicates
