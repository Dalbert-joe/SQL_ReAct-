"""
tools.py – SQL execution tools exposed to the ReAct agent.
All functions return plain dicts so they serialise cleanly to JSON.
"""
import sqlite3
import os
import json
from typing import Any

DB_PATH = os.getenv("DATABASE_URL", "database.db").replace("sqlite:///./", "")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Tool definitions sent to the model ────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "Return all table names in the database.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": "Return column names and types for a given table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Exact table name to describe.",
                    }
                },
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": (
                "Execute a read-only SQL SELECT query and return results as JSON. "
                "Never use INSERT, UPDATE, DELETE, or DROP."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A valid SQLite SELECT statement.",
                    }
                },
                "required": ["sql"],
            },
        },
    },
]


# ── Tool implementations ───────────────────────────────────────────────────────

def list_tables() -> dict:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        ).fetchall()
    return {"tables": [r["name"] for r in rows]}


def describe_table(table_name: str) -> dict:
    with _connect() as conn:
        rows = conn.execute(f"PRAGMA table_info({table_name});").fetchall()
    if not rows:
        return {"error": f"Table '{table_name}' not found."}
    return {
        "table": table_name,
        "columns": [{"name": r["name"], "type": r["type"]} for r in rows],
    }


def run_sql(sql: str) -> dict:
    sql_upper = sql.strip().upper()
    # Strict read-only guard
    forbidden = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE")
    if any(sql_upper.startswith(kw) for kw in forbidden):
        return {"error": "Only SELECT queries are permitted."}
    try:
        with _connect() as conn:
            rows = conn.execute(sql).fetchall()
        return {"rows": [dict(r) for r in rows], "count": len(rows)}
    except sqlite3.Error as e:
        return {"error": str(e)}


# ── Dispatcher ─────────────────────────────────────────────────────────────────

def dispatch(tool_name: str, arguments: dict[str, Any]) -> str:
    """Call the right tool and return its result as a JSON string."""
    if tool_name == "list_tables":
        result = list_tables()
    elif tool_name == "describe_table":
        result = describe_table(**arguments)
    elif tool_name == "run_sql":
        result = run_sql(**arguments)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    return json.dumps(result)
