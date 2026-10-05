import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listPortfolios } from "../api/query";
import type { PortfolioBook } from "../api/types";
import { Disclaimer } from "../components/Disclaimer";

function money(n: number) {
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function price(n: number) {
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function PortfolioPage() {
  const [params, setParams] = useSearchParams();
  const selectedId = Number(params.get("id") || 0);
  const [books, setBooks] = useState<PortfolioBook[]>([]);
  const [disclaimer, setDisclaimer] = useState("");
  const [error, setError] = useState("");
  const selected = books.find((p) => p.portfolio_id === selectedId) || null;

  function loadBooks() {
    return listPortfolios()
      .then((r) => {
        setBooks(r.portfolios);
        setDisclaimer(r.disclaimer);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load portfolios"));
  }

  useEffect(() => {
    void loadBooks();
  }, []);

  return (
    <section className="page">
      <h2>Current portfolios</h2>
      <p className="muted">
        Books in your assigned scope. <Link to="/app/upload">Upload a CSV</Link> to add one.
      </p>
      {error && <p className="error">{error}</p>}
      {books.length === 0 && !error && (
        <p className="muted">
          No books yet. <Link to="/app/upload">Upload a holdings CSV</Link>, or ask an admin to assign one.
        </p>
      )}
      {books.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Portfolio</th>
                <th>Manager</th>
                <th>Risk</th>
                <th>Value</th>
                <th>Benchmark</th>
              </tr>
            </thead>
            <tbody>
              {books.map((p) => (
                <tr
                  key={p.portfolio_id}
                  className={p.portfolio_id === selectedId ? "row-active" : "row-click"}
                  onClick={() => setParams({ id: String(p.portfolio_id) })}
                >
                  <td>{p.portfolio_id}</td>
                  <td>{p.portfolio_name}</td>
                  <td>{p.portfolio_manager}</td>
                  <td>
                    <span className="badge">{p.risk_category}</span>
                  </td>
                  <td>{money(p.total_value)}</td>
                  <td>{p.benchmark_index}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {selected && (
        <article className="doc-view">
          <h3>
            {selected.portfolio_name}{" "}
            <span className="badge">{selected.risk_category}</span>
          </h3>
          <p className="muted">
            {selected.portfolio_manager} · {selected.benchmark_index} · {money(selected.total_value)}
          </p>
          <div className="row">
            <button type="button" className="ghost" onClick={() => setParams({})}>
              Close
            </button>
          </div>
          {selected.holdings.length === 0 && <p className="muted">No holdings recorded for this book.</p>}
          {selected.holdings.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Asset</th>
                    <th>Type</th>
                    <th>Sector</th>
                    <th>Allocation</th>
                    <th>Market value</th>
                    <th>Buy price</th>
                    <th>Buy date</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.holdings.map((h) => (
                    <tr key={h.holding_id}>
                      <td>{h.asset_name}</td>
                      <td>{h.asset_type}</td>
                      <td>{h.sector}</td>
                      <td>{h.allocation_percentage}%</td>
                      <td>{money(h.market_value)}</td>
                      <td>{h.buy_price != null ? price(h.buy_price) : "—"}</td>
                      <td>{h.buy_date || "—"}</td>
                      <td>{h.last_updated || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      )}
      {disclaimer && <Disclaimer text={disclaimer} />}
    </section>
  );
}
