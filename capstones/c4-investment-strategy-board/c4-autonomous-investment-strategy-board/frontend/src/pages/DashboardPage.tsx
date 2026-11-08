import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BriefcaseBusiness,
  LineChart,
  Loader2,
  RefreshCw,
  Star,
  Upload,
} from "lucide-react";
import { Button, Card, EmptyState, PageHeader, PageStatus } from "@/components";
import { getDashboard } from "@/api/dashboard";
import { errorState, loadingState, successState, type AsyncState } from "@/lib/asyncState";
import { toErrorMessage } from "@/models/errors";
import type {
  AllocationSlice,
  DashboardOverview,
  IndexOverview,
  MarketOverview,
  MarketSession,
  PortfolioOverview,
  PortfolioRiskOverview,
} from "@/models";

const ENTRY_POINTS = [
  {
    to: "/portfolio",
    label: "Portfolio Analyzer",
    description: "Ask questions about an imported portfolio and review structured results.",
    icon: BriefcaseBusiness,
  },
  {
    to: "/stocks",
    label: "Stock Analyzer",
    description: "Search, select, and analyze a single instrument independently of any portfolio.",
    icon: LineChart,
  },
  {
    to: "/watchlist",
    label: "Watchlist",
    description: "Monitor selected symbols and open them in Stock Analyzer.",
    icon: Star,
  },
  {
    to: "/upload",
    label: "Upload Portfolio",
    description: "Upload a CSV or XLSX file, preview validation, then confirm import.",
    icon: Upload,
  },
] as const;

/** Independent overview screen. Detailed analysis stays on the analyzer pages. */
export function DashboardPage() {
  const [overview, setOverview] = useState<AsyncState<DashboardOverview>>(loadingState());
  const [reloadNonce, setReloadNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setOverview((current) => loadingState(current.data));
    void getDashboard()
      .then((payload) => {
        if (!cancelled) {
          setOverview(successState(payload));
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setOverview(errorState(asError(error)));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [reloadNonce]);

  const data = overview.data;
  const refreshing = overview.status === "loading" && data != null;

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Live Indian market snapshot and a high-level view of an imported portfolio. Open an analyzer for detailed research."
        actions={
          <Button
            variant="secondary"
            onClick={() => setReloadNonce((value) => value + 1)}
            disabled={overview.status === "loading"}
          >
            {overview.status === "loading" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Refresh
          </Button>
        }
      />

      <PageStatus
        loading={overview.status === "loading" && data == null}
        loadingLabel="Loading market overview..."
        error={overview.status === "error" ? overview.error : undefined}
        errorTitle="Dashboard could not be loaded"
        onRetry={() => setReloadNonce((value) => value + 1)}
      >
        {data ? (
          <div className="space-y-6">
            {refreshing ? (
              <p className="flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Updating live market data...
              </p>
            ) : null}
            <MarketSection market={data.market} />
            <PortfolioSection portfolio={data.portfolio} />
            <nav aria-label="Workspace">
              <h3 className="mb-3 text-sm font-semibold text-slate-900">Go to a workspace</h3>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {ENTRY_POINTS.map(({ to, label, description, icon: Icon }) => (
                  <Link
                    key={to}
                    to={to}
                    className="rounded-lg border border-slate-200 bg-white p-4 transition hover:border-brand-600 hover:shadow-sm"
                  >
                    <Icon className="h-4 w-4 text-brand-700" />
                    <p className="mt-2 text-sm font-semibold text-slate-900">{label}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>
                  </Link>
                ))}
              </div>
            </nav>
          </div>
        ) : null}
      </PageStatus>
    </>
  );
}

function MarketSection({ market }: { market: MarketOverview }) {
  const nifty = market.nifty50;
  const hasMarket = Boolean(nifty || market.indices.length);
  return (
    <Card
      title="Indian market"
      action={<SessionBadge session={market.session} />}
    >
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3 text-sm text-slate-600">
        <p>
          {market.trading_hours ? `Hours ${market.trading_hours}` : "Session hours unavailable"}
          {market.timezone ? ` · ${market.timezone}` : ""}
        </p>
        <p className="text-xs text-slate-500">
          Data as of {formatDate(market.as_of)}
          {market.provider ? ` · ${market.provider}` : ""}
        </p>
      </div>

      {hasMarket ? (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <NiftyCard index={nifty} />
          <div className="divide-y divide-slate-100 rounded-md border border-slate-200">
            {market.indices.map((index) => (
              <IndexRow key={index.symbol} index={index} />
            ))}
          </div>
        </div>
      ) : (
        <p className="text-sm text-amber-800">
          Live index data is unavailable from the configured market adapter. Figures are not invented.
        </p>
      )}

      {market.unavailable.length ? (
        <p className="mt-3 text-xs text-amber-800">
          Unavailable: {market.unavailable.map(humanizeField).join(", ")}.
        </p>
      ) : null}

      {market.evidence.length ? (
        <ul className="mt-3 space-y-1 text-xs text-slate-500">
          {market.evidence.map((item, index) => (
            <li key={`${item.source.provider}-${item.field}-${item.symbol}-${index}`}>
              {item.symbol ?? "Market"}
              {item.field ? ` · ${humanizeField(item.field)}` : ""}
              {` · ${item.source.provider} · ${item.source.source} · ${formatDate(item.source.timestamp)}`}
              {item.source.url ? (
                <>
                  {" · "}
                  <a className="text-brand-700 hover:underline" href={item.source.url} target="_blank" rel="noreferrer">
                    Source
                  </a>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </Card>
  );
}

function NiftyCard({ index }: { index: IndexOverview | null }) {
  if (index == null || index.value == null) {
    return (
      <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-4">
        <p className="text-sm font-semibold text-slate-900">NIFTY 50</p>
        <p className="mt-2 text-sm text-slate-500">Current level is unavailable.</p>
      </div>
    );
  }
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {index.name ?? "NIFTY 50"}
      </p>
      <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
        {formatNumber(index.value)}
      </p>
      <p className={`mt-1 text-sm tabular-nums ${signedClass(index.change)}`}>
        {formatSigned(index.change)} ({formatPercentChange(index.change_percent)}) today
      </p>
      <p className="mt-2 text-xs text-slate-500">
        {formatDate(index.timestamp)}
        {index.exchange ? ` · ${index.exchange}` : ""}
      </p>
    </div>
  );
}

function IndexRow({ index }: { index: IndexOverview }) {
  return (
    <div className="flex items-center justify-between gap-3 px-3 py-3 text-sm">
      <div>
        <p className="font-medium text-slate-900">{index.name ?? index.symbol}</p>
        <p className="text-xs text-slate-500">{index.symbol}</p>
        {index.timestamp ? (
          <p className="text-xs text-slate-400">{formatDate(index.timestamp)}</p>
        ) : null}
      </div>
      <div className="text-right">
        <p className="tabular-nums font-medium text-slate-800">{formatNumber(index.value)}</p>
        <p className={`text-xs tabular-nums ${signedClass(index.change_percent)}`}>
          {formatPercentChange(index.change_percent)}
        </p>
      </div>
    </div>
  );
}

function PortfolioSection({ portfolio }: { portfolio: PortfolioOverview | null }) {
  if (portfolio == null) {
    return (
      <Card title="Portfolio">
        <EmptyState
          title="No imported portfolio yet"
          description="Upload and confirm a holdings file to see value, allocation, and high-level risk here. Detailed questions belong on Portfolio Analyzer."
          action={
            <Link
              to="/upload"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800"
            >
              <Upload className="h-4 w-4" />
              Upload Portfolio
            </Link>
          }
        />
      </Card>
    );
  }

  const risk = portfolio.risk;
  return (
    <Card
      title={portfolio.name ?? "Imported portfolio"}
      action={
        <Link
          to={`/portfolio?portfolioId=${encodeURIComponent(portfolio.id)}`}
          className="text-sm font-medium text-brand-700 hover:text-brand-800"
        >
          Open Portfolio Analyzer
        </Link>
      }
    >
      <p className="mb-4 text-xs text-slate-500">
        Imported {formatDate(portfolio.imported_at)}
        {portfolio.evidence[0]
          ? ` · quotes from ${portfolio.evidence[0].source.provider} as of ${formatDate(portfolio.evidence[0].source.timestamp)}`
          : ""}
      </p>
      <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Portfolio value"
          value={formatMoney(portfolio.market_value, portfolio.currency)}
          hint={
            portfolio.market_value == null
              ? "Live value needs quotes for every holding"
              : portfolio.mixed_currency
                ? "Mixed currencies are not combined"
                : `${portfolio.quoted_holding_count} of ${portfolio.holding_count} holdings quoted`
          }
        />
        <Metric
          label="Today"
          value={`${formatSigned(portfolio.day_change, portfolio.currency)} (${formatPercentChange(portfolio.day_change_percent)})`}
          valueClass={signedClass(portfolio.day_change)}
        />
        <Metric label="Holdings" value={String(portfolio.holding_count)} />
        <Metric
          label="Cost value"
          value={formatMoney(portfolio.cost_value, portfolio.currency)}
          hint="Uploaded average cost, not a live market value"
        />
      </dl>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <AllocationList rows={portfolio.allocation} currency={portfolio.currency} />
        <RiskSummary risk={risk} />
      </div>

      {portfolio.unavailable.length ? (
        <p className="mt-3 text-xs text-amber-800">
          Unavailable: {portfolio.unavailable.map(humanizeField).join(", ")}. Missing prices are not filled in.
        </p>
      ) : null}
    </Card>
  );
}

function AllocationList({
  rows,
  currency,
}: {
  rows: AllocationSlice[];
  currency: string | null;
}) {
  if (!rows.length) {
    return (
      <div>
        <h4 className="text-sm font-semibold text-slate-900">Allocation</h4>
        <p className="mt-2 text-sm text-slate-500">Allocation could not be formed from the uploaded holdings.</p>
      </div>
    );
  }
  return (
    <div>
      <h4 className="text-sm font-semibold text-slate-900">Allocation</h4>
      <ul className="mt-2 space-y-2">
        {rows.map((row) => (
          <li key={row.symbol}>
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-slate-800">
                {row.symbol}
                {row.name ? <span className="ml-2 font-normal text-slate-500">{row.name}</span> : null}
              </span>
              <span className="tabular-nums text-slate-600">
                {formatWeight(row.weight)}
                {row.market_value != null ? ` · ${formatMoney(row.market_value, currency)}` : ""}
              </span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-brand-600"
                style={{ width: `${Math.max(0, Math.min(100, (row.weight ?? 0) * 100))}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RiskSummary({ risk }: { risk: PortfolioRiskOverview }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-slate-900">High-level risk</h4>
      <dl className="mt-2 grid grid-cols-2 gap-2 text-sm">
        <Indicator label="Concentration" value={humanizeField(risk.concentration)} />
        <Indicator label="Diversification" value={humanizeField(risk.diversification)} />
        <Indicator
          label="Largest holding"
          value={
            risk.largest_symbol
              ? `${risk.largest_symbol} (${formatWeight(risk.largest_weight)})`
              : "—"
          }
        />
        <Indicator label="Top 3 share" value={formatWeight(risk.top3_share)} />
        <Indicator label="Effective names" value={formatNumber(risk.effective_n, 1)} />
        <Indicator label="Weight basis" value={humanizeField(risk.weight_basis)} />
      </dl>
      {risk.oversized_symbols.length ? (
        <p className="mt-2 text-xs text-amber-800">
          Large positions: {risk.oversized_symbols.join(", ")}
        </p>
      ) : null}
    </div>
  );
}

function Metric({
  label,
  value,
  hint,
  valueClass = "text-slate-900",
}: {
  label: string;
  value: string;
  hint?: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className={`mt-1 text-lg font-semibold tabular-nums ${valueClass}`}>{value}</dd>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

function Indicator({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-slate-50 px-3 py-2">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-0.5 font-medium capitalize text-slate-800">{value}</dd>
    </div>
  );
}

function SessionBadge({ session }: { session: MarketSession }) {
  const styles: Record<MarketSession, string> = {
    open: "bg-emerald-50 text-emerald-800",
    closed: "bg-slate-100 text-slate-700",
    pre_market: "bg-amber-50 text-amber-800",
    after_hours: "bg-amber-50 text-amber-800",
    unknown: "bg-slate-100 text-slate-600",
  };
  const labels: Record<MarketSession, string> = {
    open: "Market open",
    closed: "Market closed",
    pre_market: "Pre-market",
    after_hours: "After hours",
    unknown: "Session unknown",
  };
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${styles[session]}`}>
      {labels[session]}
    </span>
  );
}

function humanizeField(field: string): string {
  return field.replaceAll("_", " ").replaceAll(":", " ");
}

function signedClass(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value) || value === 0) {
    return "text-slate-500";
  }
  return value > 0 ? "text-emerald-700" : "text-red-700";
}

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function formatSigned(value: number | null | undefined, currency?: string | null): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  const amount = Math.abs(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
  return currency ? `${sign}${amount} ${currency}` : `${sign}${amount}`;
}

function formatPercentChange(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
}

function formatMoney(value: number | null | undefined, currency: string | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  const amount = value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return currency ? `${amount} ${currency}` : amount;
}

function formatWeight(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return `${(value * 100).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function asError(error: unknown): Error {
  return error instanceof Error ? error : new Error(toErrorMessage(error));
}
