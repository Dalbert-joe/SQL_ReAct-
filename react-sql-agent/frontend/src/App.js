import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const SUGGESTED = [
  "Which department has the highest average salary?",
  "List all active projects and their departments.",
  "Who are the top 3 highest-paid employees?",
  "How many employees are in each department?",
];

function StepAccordion({ steps }) {
  const [open, setOpen] = useState(false);
  if (!steps || steps.length === 0) return null;
  return (
    <div className="accordion">
      <button className="accordion-toggle" onClick={() => setOpen((o) => !o)}>
        <span>{open ? "▾" : "▸"} Reasoning trace</span>
        <span className="step-count">{steps.length} step{steps.length !== 1 ? "s" : ""}</span>
      </button>
      {open && (
        <div className="accordion-body">
          {steps.map((s, i) => (
            <div key={i} className="step">
              <div className="step-header">
                <span className="step-num">#{i + 1}</span>
                <code className="tool-tag">{s.tool}</code>
              </div>
              {s.thought && <p className="step-thought">{s.thought}</p>}
              <pre className="step-code">{JSON.stringify(s.input, null, 2)}</pre>
              <pre className="step-result">{s.result}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Message({ msg }) {
  return (
    <div className={`msg msg--${msg.role}`}>
      <div className="msg-label">{msg.role === "user" ? "You" : "Agent"}</div>
      <div className="msg-body">
        {msg.role === "assistant" ? (
          <>
            <ReactMarkdown>{msg.content}</ReactMarkdown>
            {msg.tokens_used && (
              <span className="token-badge">~{msg.tokens_used.toLocaleString()} tokens</span>
            )}
            <StepAccordion steps={msg.steps} />
          </>
        ) : (
          <p>{msg.content}</p>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (query) => {
    const q = (query || input).trim();
    if (!q || loading) return;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Request failed");
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role:        "assistant",
          content:     data.answer,
          steps:       data.steps,
          tokens_used: data.tokens_used,
        },
      ]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <span className="logo">⬡ ReAct SQL</span>
          <span className="model-badge">gpt-4o-mini · OpenRouter</span>
        </div>
      </header>

      <main className="chat">
        {messages.length === 0 && (
          <div className="empty">
            <h1 className="empty-title">Ask your database anything.</h1>
            <p className="empty-sub">The agent will inspect schema, write SQL, and explain results.</p>
            <div className="suggestions">
              {SUGGESTED.map((s) => (
                <button key={s} className="suggestion" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <Message key={i} msg={m} />
        ))}

        {loading && (
          <div className="msg msg--assistant">
            <div className="msg-label">Agent</div>
            <div className="msg-body">
              <div className="thinking">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="error-banner">
            <strong>Error:</strong> {error}
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <footer className="composer">
        <div className="composer-inner">
          <textarea
            className="composer-input"
            rows={1}
            placeholder="Ask a question about your data…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            disabled={loading}
          />
          <button
            className="composer-btn"
            onClick={() => send()}
            disabled={!input.trim() || loading}
          >
            {loading ? "…" : "↑"}
          </button>
        </div>
      </footer>
    </div>
  );
}
