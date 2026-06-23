"""
main.py – FastAPI server bridging the React frontend to the ReAct agent.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from agent import react_loop
from database import init_db

app = FastAPI(title="ReAct-SQL-Agent", version="1.0.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()


# ── Schemas ───────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)


class StepDetail(BaseModel):
    thought: str
    tool:    str
    input:   dict
    result:  str


class QueryResponse(BaseModel):
    answer:      str
    steps:       list[StepDetail]
    tokens_used: int


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest):
    try:
        result = react_loop(request.query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
