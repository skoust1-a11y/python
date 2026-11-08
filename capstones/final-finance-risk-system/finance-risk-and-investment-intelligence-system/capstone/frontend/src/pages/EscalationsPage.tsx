import { useEffect, useState } from "react";
import { listEscalations } from "../api/query";

export function EscalationsPage() {
  const [rows, setRows] = useState<
    Array<{ escalation_id: string; trace_id: string; triggers: string[]; reviewer?: string; created_at?: string }>
  >([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listEscalations()
      .then((r) => setRows(r.escalations))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed"));
  }, []);

  return (
    <section className="page">
      <h2>Escalations</h2>
      {error && <p className="error">{error}</p>}
      {!rows.length && <p className="muted">No handoffs yet. Escalating queries will appear here.</p>}
      <ul className="list">
        {rows.map((r) => (
          <li key={r.escalation_id}>
            <strong>{r.escalation_id}</strong> · {r.triggers.join(", ")} · {r.reviewer} · {r.created_at}
          </li>
        ))}
      </ul>
    </section>
  );
}
