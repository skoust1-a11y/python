import { useEffect, useState } from "react";
import { listPortfolios, listTemplates, listUsers, patchUser, reindex } from "../api/query";
import type { PortfolioBook, User } from "../api/types";

const ALL_SCOPE_ROLES = ["risk_manager", "compliance", "admin"];

export function AdminPage() {
  const [templates, setTemplates] = useState<Array<{ query_id: string; description: string }>>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [books, setBooks] = useState<PortfolioBook[]>([]);
  const [userId, setUserId] = useState("");
  const [picked, setPicked] = useState<number[]>([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const selected = users.find((u) => u.user_id === userId) || null;
  const allScope = !!selected && ALL_SCOPE_ROLES.includes(selected.role);

  function loadUsers() {
    return listUsers()
      .then((r) => setUsers(r.users))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load users"));
  }

  useEffect(() => {
    void loadUsers();
    listPortfolios()
      .then((r) => setBooks(r.portfolios))
      .catch(() => undefined);
    listTemplates()
      .then((r) => setTemplates(r.templates))
      .catch(() => undefined);
  }, []);

  function selectUser(id: string) {
    setUserId(id);
    setPicked(users.find((u) => u.user_id === id)?.portfolio_ids || []);
    setMsg("");
    setError("");
  }

  function toggle(id: number) {
    setPicked((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id].sort((a, b) => a - b)));
  }

  async function onSave() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      await patchUser(selected.user_id, { portfolio_ids: picked });
      await loadUsers();
      setMsg(`Saved: ${selected.email} now has ${picked.length ? `portfolios ${picked.join(", ")}` : "no portfolios"}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onReindex() {
    setBusy(true);
    try {
      const r = await reindex();
      setMsg(`Policy index: ${r.chunk_count} chunks (${r.reindexed} added from PDFs).`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reindex failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page wide">
      <p className="page-kicker">Administration</p>
      <h2>Admin</h2>
      <p className="muted">Manage who can see which portfolios, and maintain the policy index.</p>
      {msg && <p className="banner">{msg}</p>}
      {error && <p className="error">{error}</p>}

      <div className="card">
        <div className="card-head">
          <h3>Users</h3>
          <span className="muted">{users.length} accounts · click a row to assign portfolios</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Portfolios</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr
                  key={u.user_id}
                  className={u.user_id === userId ? "row-active" : "row-click"}
                  onClick={() => selectUser(u.user_id)}
                >
                  <td>{u.full_name || "—"}</td>
                  <td>{u.email}</td>
                  <td>
                    <span className="badge">{u.role}</span>
                  </td>
                  <td>
                    <span className={`pill ${u.status === "active" ? "answered" : "warn"}`}>{u.status}</span>
                  </td>
                  <td>
                    {ALL_SCOPE_ROLES.includes(u.role)
                      ? "All (by role)"
                      : u.portfolio_ids.length
                        ? u.portfolio_ids.join(", ")
                        : "None"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="split">
        <div className="card">
          <div className="card-head">
            <h3>Assign portfolios</h3>
            {selected && <span className="badge">{selected.role}</span>}
          </div>
          <label>
            User
            <select value={userId} onChange={(e) => selectUser(e.target.value)}>
              <option value="">Select a user…</option>
              {users.map((u) => (
                <option key={u.user_id} value={u.user_id}>
                  {u.email}
                  {u.full_name ? ` — ${u.full_name}` : ""}
                </option>
              ))}
            </select>
          </label>
          {!selected && <p className="muted">Pick a user above or click a row in the table.</p>}
          {allScope && (
            <p className="muted">
              {selected?.email} is a {selected?.role} and already sees every portfolio. Assignment only applies to
              analysts.
            </p>
          )}
          {selected && !allScope && (
            <>
              <div className="card-head check-head">
                <span className="muted">
                  {picked.length} of {books.length} selected · saving replaces the current list
                </span>
                <div className="row-actions">
                  <button type="button" className="chip" onClick={() => setPicked(books.map((b) => b.portfolio_id))}>
                    All
                  </button>
                  <button type="button" className="chip" onClick={() => setPicked([])}>
                    None
                  </button>
                </div>
              </div>
              <div className="check-grid">
                {books.map((b) => (
                  <label key={b.portfolio_id}>
                    <input
                      type="checkbox"
                      checked={picked.includes(b.portfolio_id)}
                      onChange={() => toggle(b.portfolio_id)}
                    />
                    <span>
                      {b.portfolio_id}. {b.portfolio_name} <span className="muted">({b.risk_category})</span>
                    </span>
                  </label>
                ))}
              </div>
              <button type="button" onClick={onSave} disabled={busy}>
                {busy ? "Saving…" : "Save assignment"}
              </button>
            </>
          )}
        </div>

        <div className="card">
          <div className="card-head">
            <h3>Policy index</h3>
          </div>
          <p className="muted">Re-read the policy PDFs and embed any new chunks for retrieval.</p>
          <button type="button" className="ghost" onClick={onReindex} disabled={busy}>
            Reindex policy PDFs
          </button>
        </div>
      </div>

      <div className="card doc-view">
        <div className="card-head">
          <h3>SQL templates</h3>
          <span className="muted">{templates.length} approved queries</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Template</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.query_id}>
                  <td>
                    <code>{t.query_id}</code>
                  </td>
                  <td>{t.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
