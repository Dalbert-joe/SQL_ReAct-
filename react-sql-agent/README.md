# ReAct SQL Agent

A full-stack AI agent that answers natural-language questions about a SQLite database.  
Built with **FastAPI + OpenRouter (OpenAI SDK)** on the backend and **React** on the frontend.

```
react-sql-agent/
├── backend/
│   ├── .env.example      ← copy to .env and add your key
│   ├── requirements.txt
│   ├── database.py       ← seed script (runs automatically on startup)
│   ├── tools.py          ← list_tables / describe_table / run_sql
│   ├── agent.py          ← ReAct loop with token-budget trimming
│   └── main.py           ← FastAPI server
└── frontend/
    ├── public/index.html
    └── src/
        ├── index.js
        ├── App.js
        └── App.css
```

---

## Quick start

### 1 – Clone and configure secrets

```bash
cd backend
cp .env.example .env
# Open .env and paste your OpenRouter key
```

Your `.env`:
```
OPENROUTER_API_KEY=sk-or-v1-...
MODEL=openai/gpt-4o-mini          # swap to any OpenRouter model
MAX_ITERATIONS=8
TOKEN_BUDGET=0.85                 # keep context at 85% of limit
```

Get a key → https://openrouter.ai/keys

### 2 – Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The database is created automatically on first startup.

### 3 – Frontend

```bash
cd frontend
npm install
npm start                        # opens http://localhost:3000
```

---

## How it works

### ReAct loop (`agent.py`)

```
User question
    │
    ▼
┌─────────────────────────────────────────┐
│  Iteration (max 8)                      │
│                                         │
│  1. Send history → OpenRouter           │
│  2. Model returns tool_call or text     │
│  3. If tool_call → dispatch → observe   │
│  4. Append (assistant + tool) to history│
│  5. If text → return final answer       │
└─────────────────────────────────────────┘
```

### Token budget

Each iteration trims the conversation history so the total token count stays under **85 %** of the model's context window (128 k for gpt-4o / gpt-4o-mini).  
Oldest non-system messages are dropped first when the budget is exceeded.

```python
MAX_CTX_TOKENS = int(128_000 * 0.85)   # ≈ 108 800 tokens
```

Adjust `TOKEN_BUDGET` in `.env` (e.g. `0.90` = 90 %).

### Available tools

| Tool | What it does |
|------|-------------|
| `list_tables` | Returns all table names |
| `describe_table` | Returns columns + types for a table |
| `run_sql` | Executes a read-only SELECT query |

---

## Switching models

Change `MODEL` in `backend/.env`:

```
MODEL=anthropic/claude-3-haiku      # cheaper
MODEL=openai/gpt-4o                 # smarter
MODEL=google/gemini-flash-1.5       # fast
```

Browse all models → https://openrouter.ai/models

---

## Sample database schema

| Table | Columns |
|-------|---------|
| `employees` | id, name, dept, salary, hire_date |
| `departments` | id, name, budget |
| `projects` | id, title, dept_id, start_date, status |

---

## API

`POST /ask`
```json
{ "query": "Which department spends the most on salaries?" }
```

Response:
```json
{
  "answer": "Engineering, with a total salary spend of $500,000.",
  "steps": [
    { "thought": "...", "tool": "list_tables", "input": {}, "result": "..." },
    { "thought": "...", "tool": "run_sql",     "input": { "sql": "SELECT ..." }, "result": "..." }
  ],
  "tokens_used": 1842
}
```
