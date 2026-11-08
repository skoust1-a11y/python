import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { clearGuideline, listTypes, saveGuideline, type HouseType } from "../api/profiles";
import { deleteDocument, uploadDocument } from "../api/query";
import { useAuth } from "../auth/useAuth";
import { useProfile } from "../auth/ProfileContext";
import { Disclaimer } from "../components/Disclaimer";

export function DocumentTypePage() {
  const { useCase = "" } = useParams();
  const { user } = useAuth();
  const { profileId, profiles } = useProfile();
  const profileName = profiles.find((p) => p.profile_id === profileId)?.name || profileId;
  const [row, setRow] = useState<HouseType | null>(null);
  const [draft, setDraft] = useState("");
  const [disclaimer, setDisclaimer] = useState("");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  function refresh() {
    return listTypes(profileId)
      .then((r) => {
        const hit = r.types.find((t) => t.use_case === useCase) || null;
        setRow(hit);
        setDraft(hit?.guideline_text || "");
        setDisclaimer(r.disclaimer);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load type"));
  }

  useEffect(() => {
    refresh();
  }, [profileId, useCase]);

  if (!useCase) return <Navigate to="/app/documents" replace />;

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const text = draft.trim();
      if (!text) await clearGuideline(profileId, useCase);
      else await saveGuideline(profileId, useCase, text);
      setMsg("Guideline saved for this profile.");
      await refresh();
    } catch (err) {
      setError(detailMsg(err) || "Could not save guideline.");
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(file: File) {
    const form = new FormData();
    form.set("file", file);
    form.set("title", file.name);
    form.set("use_case", useCase);
    form.set("profile_id", profileId);
    setBusy(true);
    setError("");
    setMsg("");
    try {
      await uploadDocument(form);
      setMsg("PDF replaced for this profile.");
      await refresh();
    } catch (err) {
      setError(detailMsg(err) || "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function onRemovePdf() {
    if (!row || row.pdf_source !== "yours") return;
    setBusy(true);
    setError("");
    try {
      await deleteDocument(row.pdf.doc_id);
      setMsg("Reverted to Default PDF.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page">
      <h2>{row?.label || useCase}</h2>
      <p className="muted">
        Editing for <strong>{user?.email}</strong> · profile <strong>{profileName}</strong>.
      </p>
      {error && <p className="error">{error}</p>}
      {msg && <p>{msg}</p>}
      {!row && !error && <p className="muted">Loading…</p>}
      {row && (
        <form className="source-card" onSubmit={onSave}>
          <p className="muted">
            PDF in use:{" "}
            <Link to={`/app/documents?doc=${encodeURIComponent(row.pdf.doc_id)}`}>{row.pdf.doc_title}</Link> (
            {row.pdf_source})
          </p>
          <label>
            Guideline
            <textarea
              rows={8}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Leave empty to use Default"
            />
          </label>
          <div className="row">
            <button type="submit" disabled={busy}>
              {busy ? "Saving…" : "Save guideline"}
            </button>
            {row.guideline_source === "yours" && (
              <button
                type="button"
                className="ghost"
                disabled={busy}
                onClick={() => {
                  setDraft("");
                  clearGuideline(profileId, useCase)
                    .then(() => {
                      setMsg("Guideline cleared.");
                      return refresh();
                    })
                    .catch((err) => setError(detailMsg(err) || "Clear failed."));
                }}
              >
                Clear to Default
              </button>
            )}
          </div>
          <label>
            Replace PDF
            <input
              type="file"
              accept="application/pdf,.pdf"
              disabled={busy}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) onUpload(file);
                e.target.value = "";
              }}
            />
          </label>
          {row.pdf_source === "yours" && (
            <button type="button" className="ghost" disabled={busy} onClick={onRemovePdf}>
              Remove PDF
            </button>
          )}
        </form>
      )}
      {disclaimer && <Disclaimer text={disclaimer} />}
    </section>
  );
}

function detailMsg(err: unknown) {
  if (err instanceof ApiError && err.body && typeof err.body === "object" && "detail" in err.body) {
    return (err.body as { detail?: { message?: string } }).detail?.message || null;
  }
  return err instanceof Error ? err.message : null;
}
