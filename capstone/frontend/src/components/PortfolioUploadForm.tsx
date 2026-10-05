import { FormEvent, useState } from "react";
import { ApiError } from "../api/client";
import { uploadPortfolio } from "../api/query";

const SAMPLE_CSV =
  "asset_name,asset_type,sector,allocation_percentage,market_value,buy_price,buy_date\n" +
  "Apple Inc,Equity,Technology,10,250000,172.40,2024-03-12\n" +
  "US Treasury Bonds,Bond,Government,40,1000000,98.25,2023-11-01\n" +
  "Gold ETF,ETF,Commodity,15,375000,186.10,2024-06-20\n";

type Props = {
  onUploaded?: (portfolioId: number) => void;
};

export function PortfolioUploadForm({ onUploaded }: Props) {
  const [name, setName] = useState("");
  const [manager, setManager] = useState("");
  const [risk, setRisk] = useState("Medium");
  const [benchmark, setBenchmark] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  function downloadSample() {
    const href = URL.createObjectURL(new Blob([SAMPLE_CSV], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = href;
    a.download = "portfolio_holdings_sample.csv";
    a.click();
    URL.revokeObjectURL(href);
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem("file") as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) {
      setError("Choose a CSV file.");
      return;
    }
    const form = new FormData();
    form.set("file", file);
    form.set("portfolio_name", name);
    form.set("portfolio_manager", manager);
    form.set("risk_category", risk);
    form.set("benchmark_index", benchmark);
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const r = await uploadPortfolio(form);
      setMsg(`Uploaded ${r.portfolio.portfolio_name} (${r.portfolio.holding_count} holdings).`);
      setName("");
      if (input) input.value = "";
      onUploaded?.(r.portfolio.portfolio_id);
    } catch (err) {
      const detail =
        err instanceof ApiError && err.body && typeof err.body === "object" && "detail" in err.body
          ? (err.body as { detail?: { message?: string } }).detail?.message
          : null;
      setError(detail || (err instanceof Error ? err.message : "Upload failed."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="source-card">
      <h3>Upload your book</h3>
      <p className="muted">
        CSV columns: asset_name, asset_type, sector, allocation_percentage, market_value, buy_price, buy_date.{" "}
        <button type="button" className="ghost" onClick={downloadSample}>
          Download sample
        </button>
      </p>
      <label>
        Portfolio name
        <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={150} />
      </label>
      <div className="row">
        <label>
          Manager
          <input value={manager} onChange={(e) => setManager(e.target.value)} maxLength={150} />
        </label>
        <label>
          Risk
          <select value={risk} onChange={(e) => setRisk(e.target.value)}>
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
          </select>
        </label>
        <label>
          Benchmark
          <input value={benchmark} onChange={(e) => setBenchmark(e.target.value)} maxLength={100} />
        </label>
      </div>
      <label>
        Holdings CSV
        <input name="file" type="file" accept=".csv,text/csv" required />
      </label>
      <button type="submit" disabled={busy}>
        {busy ? "Uploading…" : "Upload CSV"}
      </button>
      {msg && <p>{msg}</p>}
      {error && <p className="error">{error}</p>}
    </form>
  );
}
