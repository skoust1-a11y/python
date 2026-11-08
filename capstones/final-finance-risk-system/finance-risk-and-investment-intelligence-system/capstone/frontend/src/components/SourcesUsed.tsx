import { Link } from "react-router-dom";
import type { Citation, QueryResponse } from "../api/types";

const ROLE_TITLE = {
  strategy: "Strategy",
  matrix: "Risk matrix",
  policy: "Other policy documents",
} as const;

const ORIGIN_LABEL = {
  system: "Built-in corpus",
  user: "Your upload",
} as const;

type DocCite = Extract<Citation, { type: "doc" }>;
type SqlCite = Extract<Citation, { type: "sql" }>;
type QuoteCite = Extract<Citation, { type: "quote" }>;
type NewsCite = Extract<Citation, { type: "news" }>;
type UsedDoc = DocCite & { sections: Array<{ section: string; page: number; excerpt?: string | null }> };

function usedDocs(citations: Citation[]): UsedDoc[] {
  const byId = new Map<string, UsedDoc>();
  for (const cite of citations) {
    if (cite.type !== "doc") continue;
    const existing = byId.get(cite.doc_id);
    const section = { section: cite.section, page: cite.page, excerpt: cite.excerpt };
    if (existing) {
      if (!existing.sections.some((s) => s.section === section.section && s.page === section.page)) {
        existing.sections.push(section);
      }
      continue;
    }
    byId.set(cite.doc_id, { ...cite, sections: [section] });
  }
  return [...byId.values()];
}

function FileCard({ doc }: { doc: UsedDoc }) {
  return (
    <article className="source-card">
      <p className="source-title">{doc.doc_title}</p>
      <p className="source-file">{doc.filename || doc.doc_id}</p>
      <p className="muted">
        {ORIGIN_LABEL[doc.origin || "system"]}
        {doc.sections.length > 0 &&
          ` · ${doc.sections.map((s) => `${s.section} p.${s.page}`).join(" · ")}`}
      </p>
      {doc.sections
        .filter((s) => s.excerpt)
        .map((s) => (
          <p key={`${s.section}-${s.page}`} className="excerpt">
            {s.excerpt}
          </p>
        ))}
      <p>
        <Link to={`/app/documents?doc=${encodeURIComponent(doc.doc_id)}`}>Read full file</Link>
      </p>
    </article>
  );
}

function RoleBlock({ role, docs }: { role: keyof typeof ROLE_TITLE; docs: UsedDoc[] }) {
  const matched = docs.filter((d) => (d.role || "policy") === role);
  return (
    <div>
      <h4>{ROLE_TITLE[role]}</h4>
      {matched.length ? (
        matched.map((doc) => <FileCard key={doc.doc_id} doc={doc} />)
      ) : (
        <p className="muted">None retrieved for this answer.</p>
      )}
    </div>
  );
}

export function SourcesUsed({
  citations,
  risk,
  evidenceSummary,
}: {
  citations: Citation[];
  risk: QueryResponse["risk"];
  evidenceSummary?: QueryResponse["evidence_summary"];
}) {
  const docs = usedDocs(citations);
  const sql = citations.filter((c): c is SqlCite => c.type === "sql");
  const quotes = citations.filter((c): c is QuoteCite => c.type === "quote");
  const news = citations.filter((c): c is NewsCite => c.type === "news");
  return (
    <div className="sources">
      <RoleBlock role="strategy" docs={docs} />
      <RoleBlock role="matrix" docs={docs} />
      <RoleBlock role="policy" docs={docs} />
      <div>
        <h4>Portfolio data</h4>
        {sql.length ? (
          <ul className="citations">
            {sql.map((c, i) => (
              <li key={`${c.query_id}-${i}`}>
                <code>{c.query_id}</code> · {c.tables.join(", ")} · {c.row_count} rows
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No SQL templates ran for this answer.</p>
        )}
      </div>
      <div>
        <h4>Current market</h4>
        {quotes.length || news.length ? (
          <ul className="citations">
            {quotes.map((c, i) => (
              <li key={`${c.symbol}-${i}`}>
                {c.symbol} {c.price}
                {c.stale ? " (stale)" : ""} · {c.provider_id} · {c.as_of}
              </li>
            ))}
            {news.map((c, i) => (
              <li key={`${c.url}-${i}`}>
                {c.headline} · {c.source} · {c.provider_id}{" "}
                <a href={c.url} target="_blank" rel="noreferrer">
                  source
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No live quotes or headlines for this answer.</p>
        )}
      </div>
      {(risk.level || risk.rationale || risk.breached_thresholds.length || risk.flagged_assets.length) && (
        <div>
          <h4>Risk applied</h4>
          <p>
            {risk.level && <span className="pill">{risk.level}</span>}
            {risk.rationale || ""}
          </p>
          {risk.breached_thresholds.map((b) => (
            <p key={b.name} className="muted">
              {b.name}: observed {b.observed_value}
              {b.unit} vs policy {b.policy_value}
              {b.unit}
            </p>
          ))}
          {risk.flagged_assets.length > 0 && (
            <p className="muted">{risk.flagged_assets.length} flagged row(s) — listed above.</p>
          )}
        </div>
      )}
      {evidenceSummary && (
        <p className="muted">
          {evidenceSummary.doc_chunks} document chunk(s) · {evidenceSummary.sql_queries} SQL
          query(ies) · {evidenceSummary.sql_rows} row(s)
          {typeof evidenceSummary.quotes === "number" ? ` · ${evidenceSummary.quotes} quote(s)` : ""}
          {typeof evidenceSummary.news === "number" ? ` · ${evidenceSummary.news} headline(s)` : ""}
        </p>
      )}
    </div>
  );
}
