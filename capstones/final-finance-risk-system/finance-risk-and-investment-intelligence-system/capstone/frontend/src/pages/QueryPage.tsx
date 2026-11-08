import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { clearSessions, deleteSession, getSessionTurns, listSessions, renameSession, streamQuery } from "../api/query";
import type { ChatSession, ChatTurn, QueryResponse } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useProfile } from "../auth/ProfileContext";
import { AnswerBody } from "../components/AnswerBody";
import { Disclaimer } from "../components/Disclaimer";
import { EscalationBanner } from "../components/EscalationBanner";
import { RoutingPanel } from "../components/RoutingPanel";
import { SourcesUsed } from "../components/SourcesUsed";
import { qualityMeters, usageLine } from "../quality";

const INFO_SAMPLES = [
  "List portfolios categorized as High risk.",
  "What diversification rules are recommended for high-risk portfolios?",
  "Are any assets exceeding the allowed risk thresholds for our portfolio strategy?",
];
const ACTION_SAMPLES = ["Override risk assessment to approve a high-risk asset."];
const ACTIVE_KEY = "frii.active_session";
const STEP_LABELS: Record<string, string> = {
  input_guard: "Safety check",
  router: "Routing question",
  retrieval: "Searching policy documents",
  portfolio_eval: "Querying portfolio data",
  market_data: "Fetching market data",
  risk: "Assessing risk",
  escalation: "Escalation review",
  synthesis: "Writing answer",
};

function isRestricted(res: QueryResponse | null): boolean {
  return res?.outcome === "escalated" || res?.outcome === "refused";
}

function pct(n: number) {
  return Math.round(Math.max(0, Math.min(1, n)) * 100);
}

function Meter({ label, hint, value }: { label: string; hint: string; value: number }) {
  const p = pct(value);
  return (
    <div className="meter">
      <div className="meter-head">
        <span>{label}</span>
        <strong>{p}%</strong>
      </div>
      <p className="muted">{hint}</p>
      <div className="meter-bar">
        <i style={{ width: `${p}%` }} />
      </div>
    </div>
  );
}

export function QueryPage() {
  const { user } = useAuth();
  const { profileId } = useProfile();
  const [params] = useSearchParams();
  const symbol = (params.get("symbol") || "").trim().toUpperCase();
  const currentOn = Boolean(user?.features.current_factors);
  const [query, setQuery] = useState(symbol ? `Single-stock research note on ${symbol}` : INFO_SAMPLES[0]);
  const [mode, setMode] = useState<"corpus" | "current">("corpus");
  const [sessionId, setSessionId] = useState<string | null>(() => localStorage.getItem(ACTIVE_KEY));
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [res, setRes] = useState<QueryResponse | null>(null);
  const [draft, setDraft] = useState("");
  const [steps, setSteps] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [pane, setPane] = useState<"explain" | "evidence">("explain");
  const ranFor = useRef("");
  const restricted = isRestricted(res);
  const samples = restricted ? INFO_SAMPLES : [...INFO_SAMPLES, ...ACTION_SAMPLES];
  const activeTitle = sessions.find((s) => s.session_id === sessionId)?.title || "New chat";
  const history = res && turns.length ? turns.slice(0, -1) : turns;

  const refreshSessions = useCallback(async () => {
    const data = await listSessions();
    setSessions(data.sessions);
  }, []);

  const openSession = useCallback(async (sid: string | null) => {
    setSessionId(sid);
    setRes(null);
    setDraft("");
    setError("");
    if (!sid) {
      localStorage.removeItem(ACTIVE_KEY);
      setTurns([]);
      return;
    }
    localStorage.setItem(ACTIVE_KEY, sid);
    const data = await getSessionTurns(sid);
    setTurns(data.turns);
  }, []);

  useEffect(() => {
    void refreshSessions().catch(() => setSessions([]));
  }, [refreshSessions]);

  useEffect(() => {
    if (!sessionId) return;
    void getSessionTurns(sessionId)
      .then((data) => setTurns(data.turns))
      .catch(() => {
        localStorage.removeItem(ACTIVE_KEY);
        setSessionId(null);
        setTurns([]);
      });
  }, [sessionId]);

  async function ask(text: string, replaceNote = false) {
    setBusy(true);
    setError("");
    setDraft("");
    setSteps([]);
    setRes(null);
    try {
      const result = await streamQuery(
        text,
        mode,
        (event, data) => {
          if (event === "progress" && data && typeof data === "object" && "node" in data) {
            const node = String((data as { node: unknown }).node);
            setSteps((prev) => [...prev, STEP_LABELS[node] || node]);
            return;
          }
          if (event === "escalation") {
            setDraft("");
            return;
          }
          if (event === "token" && data && typeof data === "object" && "text" in data) {
            const token = String((data as { text: unknown }).text || "");
            setDraft((prev) => prev + token);
          }
        },
        symbol || undefined,
        profileId,
        replaceNote,
        sessionId || undefined,
      );
      setRes(result);
      setSessionId(result.session_id);
      localStorage.setItem(ACTIVE_KEY, result.session_id);
      if (isRestricted(result)) {
        setDraft("");
      }
      const data = await getSessionTurns(result.session_id);
      setTurns(data.turns);
      await refreshSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await ask(query);
  }

  async function onRename() {
    if (!sessionId) return;
    setEditingId(sessionId);
    setEditTitle(activeTitle === "New chat" ? "" : activeTitle);
  }

  async function saveTitle(sid: string, raw: string) {
    const next = raw.trim();
    setEditingId(null);
    if (!next || next === sessions.find((s) => s.session_id === sid)?.title) return;
    await renameSession(sid, next);
    await refreshSessions();
  }

  async function onDelete(sid?: string) {
    const target = sid || sessionId;
    if (!target) return;
    const name = sessions.find((s) => s.session_id === target)?.title || "this chat";
    if (!window.confirm(`Delete “${name}”?`)) return;
    await deleteSession(target);
    if (sessionId === target) await openSession(null);
    await refreshSessions();
  }

  async function onClearAll() {
    if (!sessions.length) return;
    if (!window.confirm("Delete all previous chats?")) return;
    await clearSessions();
    await openSession(null);
    await refreshSessions();
  }

  useEffect(() => {
    if (!symbol) return;
    const text = `Single-stock research note on ${symbol}`;
    setQuery(text);
    const key = `${profileId}:${symbol}`;
    if (ranFor.current === key) return;
    ranFor.current = key;
    void ask(text);
  }, [symbol, profileId]);

  return (
    <section className="page query-workspace">
      <aside className="chat-rail">
        <button type="button" onClick={() => void openSession(null)}>
          New chat
        </button>
        {sessions.length > 0 && (
          <button type="button" className="ghost" onClick={() => void onClearAll()}>
            Clear all
          </button>
        )}
        <ul className="chat-list">
          {sessions.map((s) => (
            <li key={s.session_id} className={s.session_id === sessionId ? "chat-row active" : "chat-row"}>
              {editingId === s.session_id ? (
                <input
                  className="chat-rename"
                  value={editTitle}
                  autoFocus
                  maxLength={120}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onBlur={() => void saveTitle(s.session_id, editTitle)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void saveTitle(s.session_id, editTitle);
                    }
                    if (e.key === "Escape") setEditingId(null);
                  }}
                />
              ) : (
                <button
                  type="button"
                  className="chat-item"
                  title={s.title}
                  onClick={() => void openSession(s.session_id)}
                  onDoubleClick={() => {
                    setEditingId(s.session_id);
                    setEditTitle(s.title);
                  }}
                >
                  {s.title}
                </button>
              )}
              <button
                type="button"
                className="chat-del"
                title="Delete chat"
                aria-label={`Delete ${s.title}`}
                onClick={(e) => {
                  e.stopPropagation();
                  void onDelete(s.session_id);
                }}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <div className="query-main">
        <div className="row chat-toolbar">
          {editingId === sessionId && sessionId ? (
            <input
              className="chat-title-input"
              value={editTitle}
              autoFocus
              maxLength={120}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={() => void saveTitle(sessionId, editTitle)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void saveTitle(sessionId, editTitle);
                }
                if (e.key === "Escape") setEditingId(null);
              }}
            />
          ) : (
            <h2 title={activeTitle}>{activeTitle}</h2>
          )}
          {sessionId && (
            <>
              <button type="button" className="ghost" onClick={() => void onRename()}>
                Rename
              </button>
              <button type="button" className="ghost" onClick={() => void onDelete()}>
                Delete chat
              </button>
            </>
          )}
        </div>
        <p className="muted">
          {symbol ? (
            <>
              Analyzing <strong>{symbol}</strong>. Filings tagged with this ticker become its documents.{" "}
              <Link to={`/app/documents?symbol=${encodeURIComponent(symbol)}`}>This stock’s documents</Link>
              {" · "}
              <Link to="/app/ask">Clear ticker</Link>
            </>
          ) : (
            <>
              Need a book first? <Link to="/app/upload">Upload a holdings CSV</Link>. Follow-ups stay in this
              chat when you reuse words like “those” / “the same”.
            </>
          )}
        </p>
        {history.length > 0 && (
          <div className="thread">
            {history.map((t) => (
              <div key={t.turn_id} className="turn">
                <p className="turn-q">{t.query}</p>
                {t.answer && (
                  <div className="turn-a">
                    <span className={`pill ${t.outcome}`}>{t.outcome}</span>
                    <AnswerBody text={t.answer} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        <form className="query-form" onSubmit={onSubmit}>
          <textarea value={query} onChange={(e) => setQuery(e.target.value)} minLength={3} required rows={4} />
          <fieldset className="mode">
            <legend>Evidence</legend>
            <label>
              <input type="radio" checked={mode === "corpus"} onChange={() => setMode("corpus")} />
              Documents only
            </label>
            <label title={currentOn ? "" : "Current market/news not configured."}>
              <input
                type="radio"
                checked={mode === "current"}
                onChange={() => setMode("current")}
                disabled={!currentOn}
              />
              Documents + current
            </label>
          </fieldset>
          <div className="chips">
            {samples.map((s) => (
              <button type="button" key={s} className="chip" onClick={() => setQuery(s)}>
                {s}
              </button>
            ))}
          </div>
          {restricted && (
            <p className="muted">
              Action shortcuts are hidden while this result is escalated or refused. Reviewers use the Escalations
              page.
            </p>
          )}
          <div className="row">
            <button type="submit" disabled={busy}>
              {busy ? "Running…" : "Ask"}
            </button>
            {symbol && (
              <button type="button" className="ghost" disabled={busy} onClick={() => ask(query, true)}>
                Replace report
              </button>
            )}
          </div>
        </form>
        {error && <p className="error">{error}</p>}
        {(busy && draft) || res ? (
          <div className="ask-split">
            <div>
              {res && (
                <article className="card asked">
                  <p className="muted">Asked</p>
                  <p>{turns[turns.length - 1]?.query || query}</p>
                </article>
              )}
              {res && <EscalationBanner escalation={res.escalation} outcome={res.outcome} />}
              <article className="card answer-card">
                <div className="answer-toolbar">
                  <h3>Answer</h3>
                  {res && (
                    <>
                      <button type="button" className={pane === "explain" ? "tab active" : "tab"} onClick={() => setPane("explain")}>
                        Explain
                      </button>
                      <button type="button" className={pane === "evidence" ? "tab active" : "tab"} onClick={() => setPane("evidence")}>
                        Evidence
                      </button>
                    </>
                  )}
                </div>
                {busy && steps.length > 0 && (
                  <p className="muted" aria-live="polite">
                    {steps.map((s) => `✓ ${s}`).join("  →  ")}  → …
                  </p>
                )}
                {busy && draft && <AnswerBody text={draft} />}
                {res && (
                  <div className="result inset">
                    <p>
                      <span className={`pill ${res.outcome}`}>{res.outcome}</span>
                      {res.saved_note && <span className="pill">saved note</span>}
                      {res.risk.level && <span className="pill">{res.risk.level} risk</span>}
                      {res.risk.any_escalation_flag && <span className="pill warn">flagged</span>}
                      <span className="muted">
                        {" "}
                        {res.latency_ms} ms · {res.trace_id}
                      </span>
                    </p>
                    {pane === "explain" ? (
                      <>
                        <AnswerBody text={res.answer} />
                        <RoutingPanel routing={res.routing} evidenceMode={res.evidence_mode_used} />
                      </>
                    ) : (
                      <>
                        {(res.data_tables || []).map((table) => (
                          <div key={table.title}>
                            <h3>
                              {table.title}
                              {table.total_rows > table.rows.length
                                ? ` (${table.rows.length} of ${table.total_rows})`
                                : table.total_rows
                                  ? ` (${table.total_rows})`
                                  : ""}
                            </h3>
                            <div className="table-wrap">
                              <table>
                                <thead>
                                  <tr>
                                    {table.columns.map((c) => (
                                      <th key={c}>{c}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {table.rows.map((row, i) => (
                                    <tr key={i}>
                                      {row.map((c, j) => (
                                        <td key={j}>{c}</td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        ))}
                        <SourcesUsed citations={res.citations} risk={res.risk} evidenceSummary={res.evidence_summary} />
                      </>
                    )}
                    {res.gaps.length > 0 && <p className="muted">Gaps: {res.gaps.join("; ")}</p>}
                    <Disclaimer text={res.disclaimer} />
                  </div>
                )}
              </article>
            </div>
            <aside className="card quality-card">
              <h3>Answer quality</h3>
              <p className="muted">Scores from this run, not a separate eval suite.</p>
              {res ? (
                <>
                  {qualityMeters(res).map((m) => (
                    <Meter key={m.label} {...m} />
                  ))}
                  <p className="muted">{usageLine(res)}</p>
                </>
              ) : (
                <p className="muted">Waiting for the answer to finish.</p>
              )}
            </aside>
          </div>
        ) : null}
      </div>
    </section>
  );
}
