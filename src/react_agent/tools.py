"""This module provides tools for date retrieval and SQLite database operations.

It includes tools for getting the current date, inspecting database schema,
and executing SELECT queries on a SQLite database.
"""

import json
import sqlite3
from datetime import date
from typing import Any, Callable, List

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain.tools import ToolRuntime
from langgraph.types import Command
from pydantic import BaseModel, Field


query_list = []


@tool
def get_todays_date() -> str:
    """Get today's date in YYYY-MM-DD format."""
    print("[DEBUG] get_todays_date tool called")
    today = date.today().strftime("%Y-%m-%d")  # e.g., "2025-08-14"
    return today


@tool
def execute_sqlite_select(
    query: str, 
    runtime: ToolRuntime
) -> Command:
    """
    Execute a SELECT query on the SQLite database and return results.
    
    Use this tool to query the budget database at data/budget.db.
    Only SELECT statements are allowed for safety reasons.
    Results are returned as a list of dictionaries.
    
    Args:
        query: SQL SELECT query to execute. Must start with SELECT. Example: 'SELECT * FROM budget WHERE amount > 100'
    """
    try:
        # Enforce SELECT-only rule
        if not query.strip().lower().startswith("select"):
            return Command(
                update={
                    "query": query_list,
                    "messages": [
                        ToolMessage(
                            "Error: Only SELECT queries are allowed.",
                            tool_call_id=runtime.tool_call_id,
                        )
                    ],
                }
            )

        conn = sqlite3.connect("data/budget.db")
        cursor = conn.cursor()
        cursor.execute(query)

        rows = cursor.fetchall()
        col_names = [description[0] for description in cursor.description]
        conn.close()

        query_list.append(query)

        # Format results
        results = [dict(zip(col_names, row)) for row in rows]
        state_update = {
            "query": query_list,
            "messages": [ToolMessage(str(results), tool_call_id=runtime.tool_call_id)],
        }
        return Command(update=state_update)

    except Exception as e:
        state_update = {
            "query": query_list,
            "messages": [
                ToolMessage(f"Error executing query: {e}", tool_call_id=runtime.tool_call_id)
            ],
        }
        return Command(update=state_update)


@tool
def inspect_sqlite_db() -> str:
    """
    Inspect the complete structure of the budget database.
    
    Returns all table names, their CREATE TABLE schemas, and the first 5 sample rows
    from each table in JSON format. Use this before querying to understand the database structure.
    """
    db_path = "data/budget.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Step 1: Get all table names
        print("[DEBUG] Inspecting SQLite database at", db_path)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]

        db_info = {}

        for table in tables:
            # Step 2: Get schema
            print(f"[DEBUG] Inspecting table: {table}")
            cursor.execute(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?;",
                (table,),
            )
            schema = cursor.fetchone()["sql"]

            # Step 3: Get first 5 rows
            print(f"[DEBUG] Fetching sample rows from table: {table}")
            cursor.execute(f"SELECT * FROM {table} LIMIT 5;")
            rows = [dict(r) for r in cursor.fetchall()]

            db_info[table] = {"schema": schema, "sample_rows": rows}

        return json.dumps(db_info, indent=2)

    except sqlite3.Error as e:
        return json.dumps({"error": str(e)})

    finally:
        conn.close()


TOOLS: List[Callable[..., Any]] = [get_todays_date, inspect_sqlite_db, execute_sqlite_select]