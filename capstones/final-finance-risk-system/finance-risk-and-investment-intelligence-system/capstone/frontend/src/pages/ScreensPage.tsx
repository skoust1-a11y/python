import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listScreens, runScreen, saveScreen, screenFromNl } from "../api/screens";
import type { ScreenDefinition, ScreenRun } from "../api/types";
import { useProfile } from "../auth/ProfileContext";
import { Disclaimer } from "../components/Disclaimer";

const empty: ScreenDefinition = {
  version: 1,
  logic: "and",
  filters: [{ field: "roe", op: "gt", value: 15 }],
  sort: [{ field: "roe", dir: "desc" }],
  limit: 25,
  period: { type: "FY", as_of: "latest" },
};

export function ScreensPage() {
  const { profileId } = useProfile();
  const [nl, setNl] = useState("IT stocks with ROE > 15");
  const [def, setDef] = useState<ScreenDefinition>(empty);
  const [name, setName] = useState("High ROE");
  const [run, setRun] = useState<ScreenRun | null>(null);
  const [saved, setSaved] = useState<Array<{ screen_id: string; name: string }>>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listScreens(profileId)
      .then((r) => setSaved(r.screens))
      .catch(() => undefined);
  }, [profileId]);

  async function onNl(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await screenFromNl(nl, profileId);
      setDef(res.definition);
      setRun(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not parse screen");
    }
  }

  async function onRun(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      setRun(await runScreen(def, profileId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    }
  }

  async function onSave() {
    const res = await saveScreen(name, def, profileId);
    setSaved((s) => [...s, res]);
  }

  return (
    <section className="page">
      <h2>Stock screens</h2>
      <form onSubmit={onNl} className="row">
        <input value={nl} onChange={(e) => setNl(e.target.value)} />
        <button type="submit">From language</button>
      </form>
      <form onSubmit={onRun}>
        <label>
          Field
          <input
            value={String(def.filters[0]?.field || "")}
            onChange={(e) =>
              setDef({ ...def, filters: [{ ...def.filters[0], field: e.target.value, op: def.filters[0]?.op || "gt" }] })
            }
          />
        </label>
        <label>
          Op
          <input
            value={String(def.filters[0]?.op || "")}
            onChange={(e) =>
              setDef({ ...def, filters: [{ ...def.filters[0], op: e.target.value, field: def.filters[0]?.field || "roe" }] })
            }
          />
        </label>
        <label>
          Value
          <input
            value={String(def.filters[0]?.value ?? "")}
            onChange={(e) =>
              setDef({
                ...def,
                filters: [{ ...def.filters[0], field: def.filters[0]?.field || "roe", op: def.filters[0]?.op || "gt", value: Number(e.target.value) }],
              })
            }
          />
        </label>
        <button type="submit">Run screen</button>
      </form>
      <div className="row">
        <input value={name} onChange={(e) => setName(e.target.value)} />
        <button type="button" onClick={onSave}>
          Save
        </button>
      </div>
      {saved.length > 0 && <p className="muted">Saved: {saved.map((s) => s.name).join(", ")}</p>}
      {error && <p className="error">{error}</p>}
      {run && (
        <>
          <p>{run.row_count} rows</p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {run.columns.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {run.rows.map((row, i) => (
                  <tr key={i}>
                    {run.columns.map((c) => (
                      <td key={c}>{String(row[c] ?? "")}</td>
                    ))}
                    <td>
                      {row.symbol ? (
                        <span className="row-actions">
                          <Link className="ghost" to={`/app/ask?symbol=${encodeURIComponent(String(row.symbol))}`}>
                            Analyze
                          </Link>
                          <Link
                            className="ghost"
                            to={`/app/documents?symbol=${encodeURIComponent(String(row.symbol))}`}
                          >
                            {Number(row.docs) || 0} docs
                          </Link>
                        </span>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Disclaimer text={run.disclaimer} />
        </>
      )}
    </section>
  );
}
