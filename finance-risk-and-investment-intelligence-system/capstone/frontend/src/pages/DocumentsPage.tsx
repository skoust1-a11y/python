import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { listTypes, type HouseType } from "../api/profiles";
import { deleteDocument, getDocument, listDocuments, openDocumentFile, uploadDocument } from "../api/query";
import type { PolicyDocument, PolicyDocumentDetail } from "../api/types";
import { useProfile } from "../auth/ProfileContext";
import { Disclaimer } from "../components/Disclaimer";

const KIND_LABEL = { ar: "Annual report", concall: "Concall", ppt: "Presentation", note: "Saved note" } as const;

export function DocumentsPage() {
  const { profileId } = useProfile();
  const [params, setParams] = useSearchParams();
  const selectedId = params.get("doc") || "";
  const stock = (params.get("symbol") || "").trim().toUpperCase();
  const [types, setTypes] = useState<HouseType[]>([]);
  const [docs, setDocs] = useState<PolicyDocument[]>([]);
  const [disclaimer, setDisclaimer] = useState("");
  const [detail, setDetail] = useState<PolicyDocumentDetail | null>(null);
  const [error, setError] = useState("");
  const [fileError, setFileError] = useState("");
  const [busy, setBusy] = useState("");
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState("ar");

  function refresh() {
    if (stock) {
      return listDocuments(stock, profileId)
        .then((r) => {
          setDocs(r.documents);
          setDisclaimer(r.disclaimer);
        })
        .catch((e) => setError(e instanceof Error ? e.message : "Failed to load documents"));
    }
    return listTypes(profileId)
      .then((r) => {
        setTypes(r.types);
        setDisclaimer(r.disclaimer);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load types"));
  }

  useEffect(() => {
    refresh();
  }, [stock, profileId]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    setError("");
    getDocument(selectedId)
      .then(setDetail)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load file text"));
  }, [selectedId]);

  async function onOpenPdf() {
    if (!selectedId) return;
    setFileError("");
    try {
      await openDocumentFile(selectedId);
    } catch {
      setFileError("PDF is not available to open.");
    }
  }

  async function onUploadTicker(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem("file") as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) {
      setError("Choose a PDF file.");
      return;
    }
    const form = new FormData();
    form.set("file", file);
    form.set("title", title);
    form.set("use_case", kind);
    form.set("symbol", stock);
    form.set("profile_id", profileId);
    setBusy("ticker");
    setError("");
    try {
      const r = await uploadDocument(form);
      setTitle("");
      if (input) input.value = "";
      await refresh();
      setParams({ doc: r.document.doc_id, symbol: stock });
    } catch (err) {
      setError(detailMsg(err) || "Upload failed.");
    } finally {
      setBusy("");
    }
  }

  async function onDelete(docId: string) {
    setError("");
    try {
      await deleteDocument(docId);
      if (selectedId === docId) setParams(stock ? { symbol: stock } : {});
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    }
  }

  return (
    <section className="page">
      <h2>
        {stock ? `${stock} documents` : selectedId ? "Document in use" : "Documents in use"}
      </h2>
      <p className="muted">
        {stock ? (
          <>
            One AR / concall / ppt in use (upload replaces the previous). Saved note is output, not evidence.{" "}
            <Link to="/app/documents">House documents</Link>
            {" · "}
            <Link to={`/app/ask?symbol=${encodeURIComponent(stock)}`}>Analyze {stock}</Link>
          </>
        ) : selectedId ? (
          <>
            Showing the file currently open. <Link to="/app/documents">Back to list</Link>
          </>
        ) : (
          <>
            Current PDF per type for this profile. Edit guideline or replace the file on its form page.
          </>
        )}
      </p>
      {error && <p className="error">{error}</p>}
      {!stock && !selectedId && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>PDF in use</th>
                <th>Source</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {types.map((t) => (
                <tr key={t.use_case}>
                  <td>
                    {t.label}{" "}
                    {t.guideline_source === "yours" && <span className="badge">guideline yours</span>}
                  </td>
                  <td>
                    <Link to={`/app/documents?doc=${encodeURIComponent(t.pdf.doc_id)}`}>{t.pdf.doc_title}</Link>
                  </td>
                  <td>{t.pdf_source}</td>
                  <td>
                    <Link to={`/app/documents/type/${encodeURIComponent(t.use_case)}`}>Edit</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!stock && selectedId && !detail && <p className="muted">Loading document…</p>}
      {stock && (
        <>
          <form onSubmit={onUploadTicker} className="source-card">
            <h3>Add filing</h3>
            <label>
              Title
              <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
            </label>
            <label>
              Type
              <select value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="ar">Annual report</option>
                <option value="concall">Concall</option>
                <option value="ppt">Presentation</option>
              </select>
            </label>
            <label>
              PDF
              <input name="file" type="file" accept="application/pdf,.pdf" required />
            </label>
            <button type="submit" disabled={busy === "ticker"}>
              {busy === "ticker" ? "Indexing…" : "Upload PDF"}
            </button>
          </form>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Document</th>
                  <th>File</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr
                    key={d.doc_id}
                    className={d.doc_id === selectedId ? "row-active" : "row-click"}
                    onClick={() => setParams({ doc: d.doc_id, symbol: stock })}
                  >
                    <td>{KIND_LABEL[(d.kind || d.use_case || "ar") as keyof typeof KIND_LABEL] || d.use_case}</td>
                    <td>{d.doc_title}</td>
                    <td>
                      <code>{d.filename}</code>
                    </td>
                    <td>
                      {d.kind !== "note" && (
                        <button
                          type="button"
                          className="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDelete(d.doc_id);
                          }}
                        >
                          Remove
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {detail && detail.document.kind !== "note" && (
        <article className="doc-view">
          <h3>{detail.document.doc_title}</h3>
          <p className="source-file">{detail.document.filename}</p>
          <div className="row">
            {detail.document.has_file && (
              <button type="button" onClick={onOpenPdf}>
                Open PDF
              </button>
            )}
            <button type="button" className="ghost" onClick={() => setParams(stock ? { symbol: stock } : {})}>
              {stock ? "Close" : "Back to list"}
            </button>
          </div>
          {fileError && <p className="error">{fileError}</p>}
          {detail.chunks.length === 0 && <p className="muted">No indexed text for this file yet.</p>}
          {detail.chunks.map((c) => (
            <section key={c.chunk_id} className="source-card">
              <p className="muted">
                {c.section} · p.{c.page}
              </p>
              <pre className="excerpt">{c.chunk_text}</pre>
            </section>
          ))}
        </article>
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
