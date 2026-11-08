import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listTypes, type HouseType } from "../api/profiles";
import { listEscalations, listPortfolios, listSessions } from "../api/query";
import type { ChatSession } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useProfile } from "../auth/ProfileContext";

function ago(iso?: string | null) {
  if (!iso) return "";
  const m = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h} hr ago`;
  return `${Math.round(h / 24)} days ago`;
}

export function OverviewPage() {
  const { user } = useAuth();
  const { profileId } = useProfile();
  const canEsc = Boolean(user && ["risk_manager", "compliance", "admin"].includes(user.role));
  const [types, setTypes] = useState<HouseType[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [books, setBooks] = useState(0);
  const [esc, setEsc] = useState(0);

  useEffect(() => {
    listTypes(profileId)
      .then((r) => setTypes(r.types))
      .catch(() => setTypes([]));
    listSessions()
      .then((r) => setSessions(r.sessions))
      .catch(() => setSessions([]));
    listPortfolios()
      .then((r) => setBooks(r.portfolios.length))
      .catch(() => setBooks(0));
    if (canEsc) {
      listEscalations()
        .then((r) => setEsc(r.escalations.length))
        .catch(() => setEsc(0));
    }
  }, [profileId, canEsc]);

  const ready = types.filter((t) => t.pdf).length;

  return (
    <section className="page wide">
      <p className="page-kicker">FRII workspace</p>
      <h2>Overview</h2>
      <p className="muted">Library health and your recent Ask Knowledge activity for this profile.</p>
      <div className="kpi-row">
        <article className="kpi">
          <div>
            <p className="muted">Documents</p>
            <b>{types.length}</b>
          </div>
          <i>??</i>
        </article>
        <article className="kpi ok">
          <div>
            <p className="muted">Ready</p>
            <b>{ready}</b>
          </div>
          <i>?</i>
        </article>
        <article className="kpi">
          <div>
            <p className="muted">Portfolios</p>
            <b>{books}</b>
          </div>
          <i>?</i>
        </article>
        <article className="kpi bad">
          <div>
            <p className="muted">Escalations</p>
            <b>{canEsc ? esc : "—"}</b>
          </div>
          <i>!</i>
        </article>
      </div>
      <p className="muted">
        {sessions.length} ask thread{sessions.length === 1 ? "" : "s"} · {ready} document type
        {ready === 1 ? "" : "s"} in use
      </p>
      <div className="split">
        <article className="card">
          <div className="card-head">
            <h3>Recent activity</h3>
            <Link to="/app/ask">Ask Knowledge</Link>
          </div>
          {sessions.length === 0 ? (
            <p className="muted">No questions yet.</p>
          ) : (
            <ul className="activity">
              {sessions.slice(0, 8).map((s) => (
                <li key={s.session_id}>
                  <span>{s.title || "Ask Knowledge query"}</span>
                  <span className="pill answered">Chat</span>
                  <span className="muted">{ago(s.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="card">
          <div className="card-head">
            <h3>Recent documents</h3>
            <Link to="/app/documents">View all</Link>
          </div>
          {types.length === 0 ? (
            <p className="muted">No house documents on this profile.</p>
          ) : (
            <div>
              {types.map((t) => (
                <Link
                  key={t.use_case}
                  className="doc-row"
                  to={`/app/documents?doc=${encodeURIComponent(t.pdf.doc_id)}`}
                >
                  <strong>{t.pdf.doc_title}</strong>
                  <span className="pill answered">Ready</span>
                  <span className="muted">{t.label}</span>
                </Link>
              ))}
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
