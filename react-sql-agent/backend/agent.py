"""
agent.py – ReAct loop that drives the SQL agent via OpenRouter.

Token budget: capped at 80-90 % of a 128 k-token context window by limiting
the conversation history that gets sent on every iteration.
"""
import os
import json
import tiktoken
from openai import OpenAI
from dotenv import load_dotenv
from tools import TOOL_SCHEMAS, dispatch

load_dotenv()

# ── Client ────────────────────────────────────────────────────────────────────
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "ReAct-SQL-Agent",
    },
)

MODEL           = os.getenv("MODEL", "openai/gpt-4o-mini")
MAX_ITERATIONS  = int(os.getenv("MAX_ITERATIONS", 8))
CONTEXT_LIMIT   = 128_000          # tokens – adjust if you switch models
TOKEN_BUDGET    = float(os.getenv("TOKEN_BUDGET", 0.85))   # 85 % target
MAX_CTX_TOKENS  = int(CONTEXT_LIMIT * TOKEN_BUDGET)        # ~108 800

SYSTEM_PROMPT = """You are a precise SQL analyst. Given a natural-language question about a SQLite database:
1. Use list_tables to discover available tables.
2. Use describe_table to understand columns before writing SQL.
3. Use run_sql to execute SELECT queries.
4. Reason step-by-step (Thought → Action → Observation) until you have a confident answer.
5. Return a concise, human-readable final answer with the data in a markdown table when relevant.
Never guess table or column names—always inspect them first."""


# ── Token counting ─────────────────────────────────────────────────────────────
def _count_tokens(messages: list[dict]) -> int:
    """Approximate token count using tiktoken (cl100k_base is close enough for gpt-4o family)."""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Fallback: rough estimate
        text = json.dumps(messages)
        return len(text) // 4

    total = 0
    for msg in messages:
        total += 4  # per-message overhead
        for key, value in msg.items():
            if isinstance(value, str):
                total += len(enc.encode(value))
            elif isinstance(value, list):
                total += len(enc.encode(json.dumps(value)))
    return total


def _trim_history(messages: list[dict]) -> list[dict]:
    """
    Keep system message + recent turns so total stays under MAX_CTX_TOKENS.
    Drops oldest non-system messages first.
    """
    if _count_tokens(messages) <= MAX_CTX_TOKENS:
        return messages

    system = [m for m in messages if m["role"] == "system"]
    rest   = [m for m in messages if m["role"] != "system"]

    while rest and _count_tokens(system + rest) > MAX_CTX_TOKENS:
        rest.pop(0)   # drop oldest

    return system + rest


# ── ReAct loop ────────────────────────────────────────────────────────────────
def react_loop(user_query: str) -> dict:
    """
    Run the agent and return:
        {
          "answer": str,
          "steps":  [ {"thought": str, "tool": str, "result": str}, … ],
          "tokens_used": int
        }
    """
    history: list[dict] = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": user_query},
    ]
    steps: list[dict] = []

    for iteration in range(MAX_ITERATIONS):
        trimmed = _trim_history(history)
        tokens_so_far = _count_tokens(trimmed)

        response = client.chat.completions.create(
            model=MODEL,
            messages=trimmed,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0,
            max_tokens=1024,
        )

        msg = response.choices[0].message

        # ── Final answer (no tool call) ───────────────────────────────────────
        if not msg.tool_calls:
            return {
                "answer":      msg.content or "No answer generated.",
                "steps":       steps,
                "tokens_used": tokens_so_far,
            }

        # ── Tool call branch ──────────────────────────────────────────────────
        # Append assistant message with tool_calls
        history.append({
            "role":       "assistant",
            "content":    msg.content or "",
            "tool_calls": [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        })

        # Execute every tool call in this turn
        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            observation = dispatch(tool_name, arguments)

            steps.append({
                "thought": msg.content or f"Calling {tool_name}",
                "tool":    tool_name,
                "input":   arguments,
                "result":  observation,
            })

            history.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      observation,
            })

    # Exhausted iterations – ask model for best-effort answer
    history.append({
        "role":    "user",
        "content": "You have reached the maximum number of steps. Summarise what you found.",
    })
    trimmed = _trim_history(history)
    final = client.chat.completions.create(
        model=MODEL,
        messages=trimmed,
        temperature=0,
        max_tokens=512,
    )
    return {
        "answer":      final.choices[0].message.content or "Max iterations reached.",
        "steps":       steps,
        "tokens_used": _count_tokens(trimmed),
    }
