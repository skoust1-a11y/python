import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  Brain,
  BriefcaseBusiness,
  CircleAlert,
  Database,
  Landmark,
  Loader2,
} from "lucide-react";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, PageStatus } from "@/components";
import {
  getPortfolio,
  getPortfolioAnalysis,
  listPortfolioAnalyses,
  listPortfolios,
  submitPortfolioAnalysis,
} from "@/api/portfolios";
import { errorState, idleState, loadingState, successState, type AsyncState } from "@/lib/asyncState";
import { toErrorMessage } from "@/models/errors";
import type {
  AnalysisType,
  Evidence,
  FinalRecommendation,
  FundamentalDataSnapshot,
  Holding,
  InvestmentHorizon,
  MarketDataSnapshot,
  Portfolio,
  PortfolioAnalysisResult,
  PortfolioAnalysisSummary,
  PortfolioSummary,
  RiskAnalysisSnapshot,
  RiskTolerance,
  SpecialistResult,
  WorkflowStatus,
  CritiqueRecord,
} from "@/models";

const LARGE_POSITION_THRESHOLD = 0.2;
const HIGH_CONCENTRATION_WEIGHT = 0.4;
const HHI_LOW = 0.15;
const HHI_HIGH = 0.25;

const PREDEFINED_QUESTIONS: {
  id: string;
  topic: string;
  analysis_type: AnalysisType;
  question: string;
}[] = [
  {
    id: "concentration",
    topic: "Risk",
    analysis_type: "portfolio_risk",
    question: "How concentrated is the risk in this portfolio?",
  },
  {
    id: "review",
    topic: "Review",
    analysis_type: "portfolio_review",
    question: "Review this portfolio using current market and fundamental information.",
  },
  {
    id: "risks",
    topic: "Risk",
    analysis_type: "portfolio_risk",
    question: "What are the main risks in this portfolio given current market conditions?",
  },
  {
    id: "diversification",
    topic: "Review",
    analysis_type: "portfolio_review",
    question: "How diversified is this portfolio across holdings, and where is exposure concentrated?",
  },
  {
    id: "rebalance",
    topic: "Rebalancing",
    analysis_type: "portfolio_rebalancing",
    question: "Should this portfolio be rebalanced based on current allocation, concentration, and risk?",
  },
];

type WeightBasis = "market_value" | "uploaded_weight" | "cost_value" | "quantity_share" | "insufficient_data";
type ConcentrationLabel = "low" | "moderate" | "high" | "insufficient_data";

interface AllocationRow {
  symbol: string;
  name: string | null;
  weight: number;
}

interface PortfolioViewMetrics {
  rows: AllocationRow[];
  basis: WeightBasis;
  mixedCurrency: boolean;
  largestSymbol: string | null;
  largestWeight: number | null;
  hhi: number | null;
  effectiveN: number | null;
  top3Share: number | null;
  oversized: string[];
  concentration: ConcentrationLabel;
  totalCostValue: number | null;
  currencies: string[];
}

const BASIS_LABELS: Record<WeightBasis, string> = {
  market_value: "Current market value",
  uploaded_weight: "Uploaded weights",
  cost_value: "Cost value (not live market value)",
  quantity_share: "Quantity share (not market allocation)",
  insufficient_data: "Insufficient data",
};

const ANALYSIS_TYPE_LABELS: Record<AnalysisType, string> = {
  stock_analysis: "Stock analysis",
  portfolio_risk: "Portfolio risk",
  portfolio_review: "Portfolio review",
  portfolio_rebalancing: "Portfolio rebalancing",
};

const RISK_TOLERANCE_OPTIONS: RiskTolerance[] = ["conservative", "moderate", "aggressive"];
const HORIZON_OPTIONS: InvestmentHorizon[] = ["short", "medium", "long"];
const PORTFOLIO_ANALYSIS_TYPES: AnalysisType[] = [
  "portfolio_review",
  "portfolio_risk",
  "portfolio_rebalancing",
];

export function PortfolioAnalyzerPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const portfolioId = searchParams.get("portfolioId");

  const [catalogNonce, setCatalogNonce] = useState(0);
  const [catalog, setCatalog] = useState<AsyncState<PortfolioSummary[]>>(loadingState());
  const [detail, setDetail] = useState<AsyncState<Portfolio>>(idleState());
  const [analyses, setAnalyses] = useState<PortfolioAnalysisSummary[]>([]);
  const [result, setResult] = useState<PortfolioAnalysisResult | null>(null);
  const [resultError, setResultError] = useState<unknown>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [question, setQuestion] = useState(PREDEFINED_QUESTIONS[0].question);
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(PREDEFINED_QUESTIONS[0].id);
  const [analysisType, setAnalysisType] = useState<AnalysisType>(PREDEFINED_QUESTIONS[0].analysis_type);
  const [riskTolerance, setRiskTolerance] = useState<RiskTolerance | "">("");
  const [horizon, setHorizon] = useState<InvestmentHorizon | "">("");

  useEffect(() => {
    let cancelled = false;
    async function loadCatalog() {
      setCatalog(loadingState());
      try {
        const portfolios = await listPortfolios();
        if (cancelled) {
          return;
        }
        setCatalog(successState(portfolios, portfolios.length === 0));
      } catch (error) {
        if (!cancelled) {
          setCatalog(errorState(asError(error)));
        }
      }
    }
    void loadCatalog();
    return () => {
      cancelled = true;
    };
  }, [catalogNonce]);

  useEffect(() => {
    const portfolios = catalog.data ?? [];
    if (catalog.status !== "success" || portfolios.length === 0) {
      return;
    }
    const match = portfolioId ? portfolios.some((item) => item.id === portfolioId) : false;
    if (!match) {
      setSearchParams({ portfolioId: portfolios[0].id }, { replace: true });
    }
  }, [catalog.status, catalog.data, portfolioId, setSearchParams]);

  useEffect(() => {
    const known = catalog.data?.some((item) => item.id === portfolioId) ?? false;
    if (!portfolioId || catalog.status === "empty" || !known) {
      return;
    }
    let cancelled = false;
    async function loadDetail(id: string) {
      setDetail(loadingState());
      setResult(null);
      setResultError(null);
      setAnalyses([]);
      try {
        const [portfolio, history] = await Promise.all([getPortfolio(id), listPortfolioAnalyses(id)]);
        if (cancelled) {
          return;
        }
        setDetail(successState(portfolio));
        setAnalyses(history);
        if (history[0]) {
          try {
            const latest = await getPortfolioAnalysis(id, history[0].id);
            if (!cancelled) {
              setResult(latest);
            }
          } catch (error) {
            if (!cancelled) {
              setResultError(error);
            }
          }
        }
      } catch (error) {
        if (!cancelled) {
          setDetail(errorState(asError(error)));
        }
      }
    }
    void loadDetail(portfolioId);
    return () => {
      cancelled = true;
    };
  }, [portfolioId, catalog.status, catalog.data]);

  const portfolio = detail.data;
  const metrics = useMemo(
    () => (portfolio ? buildViewMetrics(portfolio.holdings, result) : null),
    [portfolio, result],
  );
  const marketBySymbol = useMemo(() => indexBySymbol(result?.market_data ?? []), [result]);
  const fundamentalBySymbol = useMemo(
    () => indexBySymbol(result?.fundamental_data ?? []),
    [result],
  );

  function selectPortfolio(id: string) {
    setSearchParams({ portfolioId: id });
  }

  function applyPrompt(prompt: (typeof PREDEFINED_QUESTIONS)[number]) {
    setSelectedPrompt(prompt.id);
    setQuestion(prompt.question);
    setAnalysisType(prompt.analysis_type);
  }

  function onQuestionChange(value: string) {
    setQuestion(value);
    const match = PREDEFINED_QUESTIONS.find((item) => item.question === value);
    setSelectedPrompt(match?.id ?? null);
    if (match) {
      setAnalysisType(match.analysis_type);
    }
  }

  async function runAnalysis(event: FormEvent) {
    event.preventDefault();
    if (!portfolio || analyzing) {
      return;
    }
    const text = question.trim();
    if (!text) {
      return;
    }
    setAnalyzing(true);
    setResultError(null);
    try {
      const analysis = await submitPortfolioAnalysis(portfolio.id, {
        question: text,
        analysis_type: analysisType,
        risk_tolerance: riskTolerance || null,
        horizon: horizon || null,
      });
      setResult(analysis);
      setAnalyses((current) => [
        {
          id: analysis.id,
          portfolio_id: analysis.portfolio_id,
          question: analysis.question,
          analysis_type: analysis.analysis_type,
          status: analysis.status,
          created_at: analysis.created_at,
        },
        ...current.filter((item) => item.id !== analysis.id),
      ]);
    } catch (error) {
      setResultError(error);
    } finally {
      setAnalyzing(false);
    }
  }

  async function openStoredAnalysis(analysisId: string) {
    if (!portfolio || analyzing) {
      return;
    }
    setAnalyzing(true);
    setResultError(null);
    try {
      const analysis = await getPortfolioAnalysis(portfolio.id, analysisId);
      setResult(analysis);
      setQuestion(analysis.question);
      setAnalysisType(analysis.analysis_type ?? "portfolio_review");
      const match = PREDEFINED_QUESTIONS.find((item) => item.question === analysis.question);
      setSelectedPrompt(match?.id ?? null);
    } catch (error) {
      setResultError(error);
    } finally {
      setAnalyzing(false);
    }
  }

  function reloadSelected() {
    if (!portfolioId) {
      return;
    }
    void (async () => {
      setDetail(loadingState(detail.data));
      try {
        const [portfolioRecord, history] = await Promise.all([
          getPortfolio(portfolioId),
          listPortfolioAnalyses(portfolioId),
        ]);
        setDetail(successState(portfolioRecord));
        setAnalyses(history);
      } catch (error) {
        setDetail(errorState(asError(error)));
      }
    })();
  }

  return (
    <>
      <PageHeader
        title="Portfolio Analyzer"
        description="Ask questions about an imported portfolio. Analysis combines your holdings, current market and fundamental data, and AI specialists."
        actions={
          <Button variant="secondary" onClick={() => navigate("/upload")}>
            Upload portfolio
          </Button>
        }
      />

      <PageStatus
        loading={catalog.status === "loading"}
        loadingLabel="Loading imported portfolios..."
        error={catalog.error}
        errorTitle="Imported portfolios could not be loaded"
        onRetry={() => setCatalogNonce((value) => value + 1)}
        empty={catalog.status === "empty"}
        emptyTitle="No imported portfolio"
        emptyDescription="Import a CSV or XLSX file first. Portfolio analysis is not available until holdings are confirmed."
        emptyAction={<Button onClick={() => navigate("/upload")}>Upload portfolio</Button>}
      >
        {catalog.status === "success" && catalog.data ? (
          <div className="space-y-4">
            <CompositionBanner />
            <PortfolioPicker
              portfolios={catalog.data}
              selectedId={portfolioId}
              onSelect={selectPortfolio}
            />
            <PageStatus
              loading={detail.status === "loading" || detail.status === "idle"}
              loadingLabel="Loading portfolio holdings..."
              error={detail.error}
              errorTitle="This portfolio could not be loaded"
              onRetry={reloadSelected}
              empty={detail.status === "empty"}
              emptyTitle="Portfolio is empty"
              emptyDescription="This imported portfolio has no holdings to analyze."
            >
              {portfolio && metrics ? (
                <div className="space-y-4">
                  <SummaryCard portfolio={portfolio} metrics={metrics} />
                  <HoldingsCard
                    holdings={portfolio.holdings}
                    metrics={metrics}
                    marketBySymbol={marketBySymbol}
                    fundamentalBySymbol={fundamentalBySymbol}
                  />
                  <div className="grid gap-4 lg:grid-cols-2">
                    <AllocationCard metrics={metrics} />
                    <ConcentrationCard metrics={metrics} risk={result?.risk_analysis ?? null} />
                  </div>
                  <RiskAndMetricsCard
                    portfolio={portfolio}
                    metrics={metrics}
                    result={result}
                  />
                  <AskCard
                    question={question}
                    selectedPrompt={selectedPrompt}
                    analysisType={analysisType}
                    riskTolerance={riskTolerance}
                    horizon={horizon}
                    analyzing={analyzing}
                    onQuestionChange={onQuestionChange}
                    onSelectPrompt={applyPrompt}
                    onAnalysisTypeChange={setAnalysisType}
                    onRiskToleranceChange={setRiskTolerance}
                    onHorizonChange={setHorizon}
                    onSubmit={runAnalysis}
                  />
                  {analyses.length ? (
                    <PriorRuns analyses={analyses} activeId={result?.id ?? null} onOpen={openStoredAnalysis} />
                  ) : null}
                  <AnalysisOutput analyzing={analyzing} error={resultError} result={result} />
                </div>
              ) : null}
            </PageStatus>
          </div>
        ) : null}
      </PageStatus>
    </>
  );
}

function CompositionBanner() {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        What this analysis uses
      </p>
      <p className="mt-1 text-sm font-medium text-slate-900">
        User portfolio data + current external market/fundamental information + AI specialist analysis
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <CompositionStep
          icon={<Database className="h-4 w-4" />}
          title="Your holdings"
          body="Imported symbols, quantities, and any weights or cost basis you uploaded. This is the only user-provided financial dataset."
        />
        <CompositionStep
          icon={<Landmark className="h-4 w-4" />}
          title="Current market & fundamentals"
          body="Quotes, history, and reported fundamentals retrieved at analysis time. Missing fields stay missing."
        />
        <CompositionStep
          icon={<Brain className="h-4 w-4" />}
          title="AI specialists"
          body="Market, fundamental, risk, and optional optimization agents interpret retrieved evidence. Trades are not executed."
        />
      </div>
    </Card>
  );
}

function CompositionStep({
  icon,
  title,
  body,
}: {
  icon: ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
      <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
        <span className="text-brand-700">{icon}</span>
        {title}
      </div>
      <p className="mt-1 text-xs leading-5 text-slate-500">{body}</p>
    </div>
  );
}

function PortfolioPicker({
  portfolios,
  selectedId,
  onSelect,
}: {
  portfolios: PortfolioSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <Card title="Imported portfolio">
      <label className="block text-sm">
        <span className="font-medium text-slate-700">Select a confirmed portfolio</span>
        <select
          className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-600"
          value={selectedId ?? ""}
          onChange={(event) => onSelect(event.target.value)}
        >
          {portfolios.map((item) => (
            <option key={item.id} value={item.id}>
              {portfolioLabel(item)} · {item.holding_count}{" "}
              {item.holding_count === 1 ? "holding" : "holdings"}
            </option>
          ))}
        </select>
      </label>
    </Card>
  );
}

function SummaryCard({
  portfolio,
  metrics,
}: {
  portfolio: Portfolio;
  metrics: PortfolioViewMetrics;
}) {
  return (
    <Card title="Portfolio summary">
      <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Name" value={portfolio.name ?? "Untitled portfolio"} />
        <Metric label="Holdings" value={String(portfolio.holding_count)} />
        <Metric label="Source" value={`${portfolio.source_filename} (${portfolio.source_format.toUpperCase()})`} />
        <Metric label="Imported" value={formatDate(portfolio.imported_at)} />
        <Metric label="Base currency" value={portfolio.base_currency ?? "—"} />
        <Metric label="Allocation basis" value={BASIS_LABELS[metrics.basis]} />
        <Metric label="Total cost value" value={formatMoney(metrics.totalCostValue, portfolio.base_currency)} />
        <Metric
          label="Currencies"
          value={metrics.currencies.length ? metrics.currencies.join(", ") : "—"}
        />
      </dl>
      {metrics.mixedCurrency ? (
        <p className="mt-3 text-sm text-amber-800">
          Holdings use more than one currency. Market-value totals are not combined without FX conversion.
        </p>
      ) : null}
    </Card>
  );
}

function HoldingsCard({
  holdings,
  metrics,
  marketBySymbol,
  fundamentalBySymbol,
}: {
  holdings: Holding[];
  metrics: PortfolioViewMetrics;
  marketBySymbol: Map<string, MarketDataSnapshot>;
  fundamentalBySymbol: Map<string, FundamentalDataSnapshot>;
}) {
  const weightBySymbol = new Map(metrics.rows.map((row) => [row.symbol, row.weight]));
  const hasMarket = marketBySymbol.size > 0;

  return (
    <Card title="Holdings">
      {holdings.length === 0 ? (
        <p className="text-sm text-slate-500">No holdings in this portfolio.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-2 py-2 font-medium">Symbol</th>
                <th className="px-2 py-2 font-medium">Name</th>
                <th className="px-2 py-2 font-medium">Quantity</th>
                <th className="px-2 py-2 font-medium">Avg cost</th>
                <th className="px-2 py-2 font-medium">Weight</th>
                <th className="px-2 py-2 font-medium">Cost value</th>
                {hasMarket ? <th className="px-2 py-2 font-medium">Last price</th> : null}
                <th className="px-2 py-2 font-medium">Analyze holding</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => {
                const market = marketBySymbol.get(holding.symbol);
                const fundamental = fundamentalBySymbol.get(holding.symbol);
                const displayName = holding.name ?? fundamental?.company_name ?? "—";
                return (
                  <tr key={holding.symbol} className="border-b border-slate-100">
                    <td className="px-2 py-2 font-medium text-slate-800">
                      <Link className="text-brand-700 hover:underline" to={stockPath(holding.symbol)}>
                        {holding.symbol}
                      </Link>
                    </td>
                    <td className="px-2 py-2 text-slate-600">
                      {displayName}
                      {fundamental?.sector ? (
                        <span className="mt-0.5 block text-xs text-slate-400">{fundamental.sector}</span>
                      ) : null}
                    </td>
                    <td className="px-2 py-2 tabular-nums">{formatNumber(holding.quantity)}</td>
                    <td className="px-2 py-2 tabular-nums">
                      {formatMoney(holding.average_cost, holding.currency)}
                    </td>
                    <td className="px-2 py-2 tabular-nums">
                      {formatWeight(weightBySymbol.get(holding.symbol) ?? holding.weight)}
                    </td>
                    <td className="px-2 py-2 tabular-nums">
                      {formatMoney(holding.cost_value, holding.currency)}
                    </td>
                    {hasMarket ? (
                      <td className="px-2 py-2 tabular-nums">
                        {formatMoney(market?.current_price ?? null, market?.currency ?? holding.currency)}
                        {market?.as_of ? (
                          <span className="mt-0.5 block text-xs text-slate-400">
                            {formatDate(market.as_of)}
                            {market.source ? ` · ${market.source.provider}` : ""}
                          </span>
                        ) : null}
                      </td>
                    ) : null}
                    <td className="px-2 py-2">
                      <Link
                        className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline"
                        to={stockPath(holding.symbol)}
                      >
                        Analyze holding
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-xs text-slate-500">
        Analyze a holding in Stock Analyzer for single-instrument research. That view does not reuse this
        portfolio run.
      </p>
    </Card>
  );
}

function AllocationCard({ metrics }: { metrics: PortfolioViewMetrics }) {
  const sorted = [...metrics.rows].sort((left, right) => right.weight - left.weight);
  return (
    <Card title="Allocation">
      <p className="mb-3 text-xs text-slate-500">{BASIS_LABELS[metrics.basis]}</p>
      {sorted.length === 0 ? (
        <p className="text-sm text-slate-500">Allocation cannot be formed from the available holdings.</p>
      ) : (
        <ul className="space-y-2">
          {sorted.map((row) => (
            <li key={row.symbol}>
              <div className="flex items-center justify-between text-sm">
                <Link className="font-medium text-brand-700 hover:underline" to={stockPath(row.symbol)}>
                  {row.symbol}
                </Link>
                <span className="tabular-nums text-slate-600">{formatWeight(row.weight)}</span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-brand-600"
                  style={{ width: `${Math.min(row.weight * 100, 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function ConcentrationCard({
  metrics,
  risk,
}: {
  metrics: PortfolioViewMetrics;
  risk: RiskAnalysisSnapshot | null;
}) {
  const largestSymbol = risk?.largest_symbol ?? metrics.largestSymbol;
  const largestWeight = risk?.largest_weight ?? metrics.largestWeight;
  const hhi = risk?.hhi ?? metrics.hhi;
  const label = risk?.concentration ?? metrics.concentration;
  return (
    <Card title="Concentration">
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <Metric label="Largest holding" value={largestSymbol ?? "—"} />
        <Metric label="Largest weight" value={formatWeight(largestWeight)} />
        <Metric label="HHI" value={formatNumber(hhi, 3)} />
        <Metric label="Effective N" value={formatNumber(metrics.effectiveN, 2)} />
        <Metric label="Top 3 share" value={formatWeight(metrics.top3Share)} />
        <Metric label="Concentration" value={label ?? "—"} />
      </dl>
      {metrics.oversized.length ? (
        <p className="mt-3 text-sm text-amber-800">
          Positions at or above {(LARGE_POSITION_THRESHOLD * 100).toFixed(0)}%:{" "}
          {metrics.oversized.map((symbol, index) => (
            <span key={symbol}>
              {index > 0 ? ", " : ""}
              <Link className="font-medium text-brand-700 hover:underline" to={stockPath(symbol)}>
                {symbol}
              </Link>
            </span>
          ))}
        </p>
      ) : (
        <p className="mt-3 text-xs text-slate-500">No holding is at or above the 20% size threshold.</p>
      )}
    </Card>
  );
}

function RiskAndMetricsCard({
  portfolio,
  metrics,
  result,
}: {
  portfolio: Portfolio;
  metrics: PortfolioViewMetrics;
  result: PortfolioAnalysisResult | null;
}) {
  const risk = result?.risk_analysis ?? null;
  const marketCount = result?.market_data.length ?? 0;
  const fundamentalCount = result?.fundamental_data.length ?? 0;
  return (
    <Card title="Risk indicators and portfolio metrics">
      <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Overall risk" value={risk?.overall_risk_assessment ?? "Run analysis to retrieve"} />
        <Metric label="Diversification" value={risk?.diversification ?? "—"} />
        <Metric label="Portfolio volatility" value={formatPercent(risk?.portfolio_volatility)} />
        <Metric label="Max drawdown" value={formatPercent(risk?.max_drawdown)} />
        <Metric label="Weight basis" value={risk?.weight_basis ?? BASIS_LABELS[metrics.basis]} />
        <Metric label="Holding count" value={String(portfolio.holding_count)} />
        <Metric
          label="Market snapshots"
          value={result ? String(marketCount) : "Not retrieved yet"}
        />
        <Metric
          label="Fundamental snapshots"
          value={result ? String(fundamentalCount) : "Not retrieved yet"}
        />
      </dl>
      {risk?.major_risks.length ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
          {risk.major_risks.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
      {risk?.unavailable.length ? (
        <p className="mt-3 text-sm text-amber-800">
          Unavailable risk fields: {risk.unavailable.join(", ")}.
        </p>
      ) : null}
      {!result ? (
        <p className="mt-3 text-sm text-slate-500">
          Market-based volatility, drawdown, and specialist risk labels are produced when you run
          analysis. Figures above that come from holdings alone are not live market values.
        </p>
      ) : null}
    </Card>
  );
}

function AskCard({
  question,
  selectedPrompt,
  analysisType,
  riskTolerance,
  horizon,
  analyzing,
  onQuestionChange,
  onSelectPrompt,
  onAnalysisTypeChange,
  onRiskToleranceChange,
  onHorizonChange,
  onSubmit,
}: {
  question: string;
  selectedPrompt: string | null;
  analysisType: AnalysisType;
  riskTolerance: RiskTolerance | "";
  horizon: InvestmentHorizon | "";
  analyzing: boolean;
  onQuestionChange: (value: string) => void;
  onSelectPrompt: (prompt: (typeof PREDEFINED_QUESTIONS)[number]) => void;
  onAnalysisTypeChange: (value: AnalysisType) => void;
  onRiskToleranceChange: (value: RiskTolerance | "") => void;
  onHorizonChange: (value: InvestmentHorizon | "") => void;
  onSubmit: (event: FormEvent) => void;
}) {
  const canSubmit = question.trim().length > 0 && !analyzing;
  return (
    <Card title="Ask the strategy board">
      <form className="space-y-4" onSubmit={onSubmit}>
        <div>
          <p className="text-sm font-medium text-slate-700">Predefined questions</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {PREDEFINED_QUESTIONS.map((prompt) => {
              const active = selectedPrompt === prompt.id;
              return (
                <li key={prompt.id}>
                  <button
                    type="button"
                    className={`rounded-full px-3 py-1.5 text-left text-xs font-medium ${
                      active
                        ? "bg-brand-700 text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                    onClick={() => onSelectPrompt(prompt)}
                    disabled={analyzing}
                  >
                    {prompt.question}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        <label className="block text-sm">
          <span className="font-medium text-slate-700">Custom question</span>
          <textarea
            className="mt-1 min-h-[96px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-600"
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            placeholder="Ask about concentration, diversification, or rebalancing using this imported book."
            maxLength={2000}
            disabled={analyzing}
          />
        </label>

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Analysis type</span>
            <select
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-600"
              value={analysisType}
              onChange={(event) => onAnalysisTypeChange(event.target.value as AnalysisType)}
              disabled={analyzing}
            >
              {PORTFOLIO_ANALYSIS_TYPES.map((item) => (
                <option key={item} value={item}>
                  {ANALYSIS_TYPE_LABELS[item]}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Risk tolerance</span>
            <select
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-600"
              value={riskTolerance}
              onChange={(event) => onRiskToleranceChange(event.target.value as RiskTolerance | "")}
              disabled={analyzing}
            >
              <option value="">Not specified</option>
              {RISK_TOLERANCE_OPTIONS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Horizon</span>
            <select
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-600"
              value={horizon}
              onChange={(event) => onHorizonChange(event.target.value as InvestmentHorizon | "")}
              disabled={analyzing}
            >
              <option value="">Not specified</option>
              {HORIZON_OPTIONS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={!canSubmit}>
            {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <BriefcaseBusiness className="h-4 w-4" />}
            {analyzing ? "Running analysis..." : "Run analysis"}
          </Button>
          <p className="text-xs text-slate-500">
            Uses this imported book, retrieved market/fundamental data, and specialist agents. No trades
            are placed.
          </p>
        </div>
      </form>
    </Card>
  );
}

function PriorRuns({
  analyses,
  activeId,
  onOpen,
}: {
  analyses: PortfolioAnalysisSummary[];
  activeId: string | null;
  onOpen: (id: string) => void;
}) {
  return (
    <Card title="Stored runs">
      <ul className="space-y-2">
        {analyses.map((item) => {
          const active = item.id === activeId;
          return (
            <li key={item.id}>
              <button
                type="button"
                className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                  active ? "bg-brand-50 text-brand-800" : "bg-slate-50 text-slate-700 hover:bg-slate-100"
                }`}
                onClick={() => onOpen(item.id)}
              >
                <span className="font-medium">{item.question}</span>
                <span className="mt-0.5 block text-xs text-slate-500">
                  {item.analysis_type ? ANALYSIS_TYPE_LABELS[item.analysis_type] : "Unspecified type"} ·{" "}
                  {item.status} · {formatDate(item.created_at)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function AnalysisOutput({
  analyzing,
  error,
  result,
}: {
  analyzing: boolean;
  error: unknown;
  result: PortfolioAnalysisResult | null;
}) {
  if (analyzing) {
    return (
      <div
        className="rounded-lg border border-brand-100 bg-brand-50 px-4 py-8"
        role="status"
        aria-live="polite"
      >
        <LoadingState label="Specialists are analyzing your holdings with current market and fundamental data..." />
      </div>
    );
  }
  if (error) {
    return <ErrorState error={error} title="Analysis could not be completed" />;
  }
  if (!result) {
    return (
      <EmptyState
        title="No analysis yet"
        description="Choose a predefined question or write your own, then run analysis. The report, evidence, recommendation, and limitations will appear here."
      />
    );
  }
  return <AnalysisReport result={result} />;
}

function AnalysisReport({ result }: { result: PortfolioAnalysisResult }) {
  const recommendation = result.recommendation;
  return (
    <div className="space-y-4">
      <Card title="Structured AI report">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={result.status} />
          {result.analysis_type ? (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
              {ANALYSIS_TYPE_LABELS[result.analysis_type]}
            </span>
          ) : null}
        </div>
        <p className="mt-3 text-sm text-slate-700">
          <span className="font-medium text-slate-900">Question: </span>
          {result.question}
        </p>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Started" value={formatDate(result.execution.started_at)} />
          <Metric label="Completed" value={formatDate(result.execution.completed_at)} />
          <Metric
            label="Duration"
            value={result.execution.duration_ms != null ? `${result.execution.duration_ms} ms` : "—"}
          />
          <Metric
            label="Specialists invoked"
            value={result.execution.invoked_agents.join(", ") || "—"}
          />
        </dl>
        {result.execution.errors.length ? (
          <ul className="mt-3 space-y-1 text-sm text-red-700">
            {result.execution.errors.map((item) => (
              <li key={item} className="flex items-start gap-2">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        ) : null}
        {recommendation ? (
          <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
            <p className="font-medium text-slate-900">Synthesis</p>
            <p className="mt-1">{recommendation.summary}</p>
          </div>
        ) : null}
      </Card>

      <Card title="Specialist findings">
        {result.specialist_results.length === 0 ? (
          <p className="text-sm text-slate-500">No specialist summaries were returned for this run.</p>
        ) : (
          <ul className="space-y-3">
            {result.specialist_results.map((item) => (
              <li key={item.agent} className="rounded-md border border-slate-200 px-3 py-3">
                <SpecialistBlock result={item} />
              </li>
            ))}
          </ul>
        )}
      </Card>

      <CritiqueCard critiques={result.critiques ?? []} />

      {result.conflicts.length ? (
        <Card title="Conflicts">
          <ul className="space-y-2 text-sm">
            {result.conflicts.map((conflict, index) => (
              <li key={`${conflict.description}-${index}`} className="rounded-md bg-amber-50 px-3 py-2 text-amber-900">
                <span className="font-medium">{conflict.severity}: </span>
                {conflict.description}
                {conflict.agents.length ? (
                  <span className="mt-0.5 block text-xs">Agents: {conflict.agents.join(", ")}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {result.optimization ? (
        <Card title="Optimization snapshot">
          <p className="text-sm text-slate-600">
            Objective: {result.optimization.objective ?? "—"} · Feasible:{" "}
            {result.optimization.feasible == null ? "—" : result.optimization.feasible ? "yes" : "no"} ·
            Trade execution: {result.optimization.trade_execution.replace("_", " ")}
          </p>
          {Object.keys(result.optimization.proposed_allocation).length ? (
            <ul className="mt-3 space-y-1 text-sm">
              {Object.entries(result.optimization.proposed_allocation)
                .sort((left, right) => right[1] - left[1])
                .map(([symbol, weight]) => (
                  <li key={symbol} className="flex justify-between">
                    <Link className="font-medium text-brand-700 hover:underline" to={stockPath(symbol)}>
                      {symbol}
                    </Link>
                    <span className="tabular-nums">{formatWeight(weight)}</span>
                  </li>
                ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-500">No proposed allocation was returned.</p>
          )}
        </Card>
      ) : null}

      <RecommendationCard recommendation={recommendation} />
      <EvidenceCard evidence={result.evidence} market={result.market_data} fundamentals={result.fundamental_data} />
      <LimitationsCard recommendation={recommendation} result={result} />
    </div>
  );
}

function SpecialistBlock({ result }: { result: SpecialistResult }) {
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-slate-900">{result.role}</p>
          <p className="text-xs text-slate-500">{result.agent}</p>
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            result.status === "succeeded" ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800"
          }`}
        >
          {result.status}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-700">{result.summary}</p>
      {result.findings.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
          {result.findings.map((finding) => (
            <li key={finding}>{finding}</li>
          ))}
        </ul>
      ) : null}
      {result.confidence != null ? (
        <p className="mt-2 text-xs text-slate-500">Confidence {formatWeight(result.confidence)}</p>
      ) : null}
      {result.error_message ? (
        <p className="mt-2 text-sm text-red-700">{result.error_message}</p>
      ) : null}
    </>
  );
}

function CritiqueCard({ critiques }: { critiques: CritiqueRecord[] }) {
  return (
    <Card title="Critique">
      {critiques.length === 0 ? (
        <p className="text-sm text-slate-500">
          No critique findings were raised. Specialists agreed enough to skip a review cycle.
        </p>
      ) : (
        <ul className="space-y-2 text-sm">
          {critiques.map((item, index) => (
            <li
              key={`${item.author}-${item.category}-${item.message}-${index}`}
              className={`rounded-md px-3 py-2 ${
                item.severity === "critical" ? "bg-red-50 text-red-800" : "bg-amber-50 text-amber-900"
              }`}
            >
              <span className="font-medium">
                {item.severity}
                {item.category ? ` · ${item.category.replaceAll("_", " ")}` : ""}
                {item.resolved ? " · resolved" : ""}
              </span>
              <span className="mt-0.5 block">{item.message}</span>
              <span className="mt-0.5 block text-xs opacity-80">
                {item.author}
                {item.target ? ` · ${item.target}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function RecommendationCard({ recommendation }: { recommendation: FinalRecommendation | null }) {
  return (
    <Card title="Recommendation">
      {!recommendation ? (
        <p className="text-sm text-slate-500">No recommendation was produced for this run.</p>
      ) : (
        <div className="space-y-3 text-sm text-slate-700">
          <p className="font-medium text-slate-900">{recommendation.recommendation}</p>
          {recommendation.findings.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Findings</p>
              <ul className="mt-1 list-disc space-y-1 pl-5">
                {recommendation.findings.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {recommendation.risks.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Risks</p>
              <ul className="mt-1 list-disc space-y-1 pl-5">
                {recommendation.risks.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <p className="text-xs text-slate-500">
            Confidence {recommendation.confidence == null ? "—" : formatWeight(recommendation.confidence)} ·
            Trade execution {recommendation.trade_execution.replace("_", " ")}
          </p>
        </div>
      )}
    </Card>
  );
}

function EvidenceCard({
  evidence,
  market,
  fundamentals,
}: {
  evidence: Evidence[];
  market: MarketDataSnapshot[];
  fundamentals: FundamentalDataSnapshot[];
}) {
  return (
    <Card title="Evidence and sources">
      <p className="text-sm text-slate-600">
        Retrieved from configured market and fundamental providers during this run. Values are not
        invented when a source is missing.
      </p>
      {market.length || fundamentals.length ? (
        <p className="mt-2 text-xs text-slate-500">
          {market.length} market snapshot{market.length === 1 ? "" : "s"} · {fundamentals.length}{" "}
          fundamental snapshot{fundamentals.length === 1 ? "" : "s"}
        </p>
      ) : null}
      {evidence.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">No evidence items were attached to this result.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {evidence.map((item, index) => (
            <li
              key={`${item.source.provider}-${item.symbol}-${item.field}-${index}`}
              className="rounded-md border border-slate-200 px-3 py-2 text-sm"
            >
              <p className="font-medium text-slate-800">
                {item.symbol ?? "Portfolio"}
                {item.field ? ` · ${item.field}` : ""}
                {item.value != null ? ` · ${String(item.value)}` : ""}
              </p>
              {item.excerpt ? <p className="mt-1 text-slate-600">{item.excerpt}</p> : null}
              <p className="mt-1 text-xs text-slate-500">
                {item.source.provider} · {item.source.source} · {formatDate(item.source.timestamp)}
                {item.period ? ` · ${item.period}` : ""}
                {item.source.url ? ` · ${item.source.url}` : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function LimitationsCard({
  recommendation,
  result,
}: {
  recommendation: FinalRecommendation | null;
  result: PortfolioAnalysisResult;
}) {
  const assumptions = recommendation?.assumptions ?? [];
  const limitations = [
    ...(recommendation?.limitations ?? []),
    ...(result.optimization?.limitations ?? []),
  ];
  const warnings = result.optimization?.warnings ?? [];
  return (
    <Card title="Limitations and assumptions">
      {!assumptions.length && !limitations.length && !warnings.length ? (
        <p className="text-sm text-slate-500">
          No explicit limitations were returned. Analysis still depends on uploaded holdings, retrieved
          snapshots, and specialist interpretation. Missing market or fundamental fields are not filled
          in.
        </p>
      ) : (
        <div className="grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Assumptions</p>
            {assumptions.length ? (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-700">
                {assumptions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-slate-500">None recorded.</p>
            )}
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Limitations</p>
            {limitations.length || warnings.length ? (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-700">
                {limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
                {warnings.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-slate-500">None recorded.</p>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-800">{value}</dd>
    </div>
  );
}

function StatusBadge({ status }: { status: WorkflowStatus }) {
  const styles: Record<WorkflowStatus, string> = {
    pending: "bg-slate-100 text-slate-700",
    running: "bg-brand-50 text-brand-800",
    completed: "bg-emerald-50 text-emerald-800",
    failed: "bg-red-50 text-red-800",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}>{status}</span>
  );
}

function buildViewMetrics(
  holdings: Holding[],
  result: PortfolioAnalysisResult | null,
): PortfolioViewMetrics {
  const currencies = [...new Set(holdings.map((item) => item.currency).filter((item): item is string => Boolean(item)))];
  const mixedCurrency = currencies.length > 1;
  const totalCostValue =
    holdings.length && holdings.every((item) => item.cost_value != null)
      ? holdings.reduce((sum, item) => sum + (item.cost_value ?? 0), 0)
      : null;

  const local = resolveAllocation(holdings, mixedCurrency);
  const market = marketValueAllocation(holdings, result?.market_data ?? [], mixedCurrency);
  const chosen = market ?? local;
  const hhi = herfindahl(chosen.rows.map((row) => row.weight));
  const largest = chosen.rows.reduce<AllocationRow | null>(
    (current, row) => (!current || row.weight > current.weight ? row : current),
    null,
  );
  const top3Share = [...chosen.rows]
    .sort((left, right) => right.weight - left.weight)
    .slice(0, 3)
    .reduce((sum, row) => sum + row.weight, 0);
  const oversized = chosen.rows
    .filter((row) => row.weight >= LARGE_POSITION_THRESHOLD)
    .map((row) => row.symbol)
    .sort();

  return {
    rows: chosen.rows,
    basis: chosen.basis,
    mixedCurrency,
    largestSymbol: result?.risk_analysis?.largest_symbol ?? largest?.symbol ?? null,
    largestWeight: result?.risk_analysis?.largest_weight ?? largest?.weight ?? null,
    hhi: result?.risk_analysis?.hhi ?? hhi,
    effectiveN: hhi && hhi > 0 ? 1 / hhi : null,
    top3Share: chosen.rows.length ? top3Share : null,
    oversized,
    concentration: classifyConcentration(result?.risk_analysis?.hhi ?? hhi, largest?.weight ?? null),
    totalCostValue,
    currencies,
  };
}

function resolveAllocation(
  holdings: Holding[],
  mixedCurrency: boolean,
): { rows: AllocationRow[]; basis: WeightBasis } {
  if (holdings.every((item) => item.weight != null)) {
    const total = holdings.reduce((sum, item) => sum + (item.weight ?? 0), 0);
    if (total > 0) {
      return {
        basis: "uploaded_weight",
        rows: holdings.map((item) => ({
          symbol: item.symbol,
          name: item.name,
          weight: (item.weight ?? 0) / total,
        })),
      };
    }
  }
  if (!mixedCurrency && holdings.every((item) => item.cost_value != null && (item.cost_value ?? 0) > 0)) {
    const total = holdings.reduce((sum, item) => sum + (item.cost_value ?? 0), 0);
    return {
      basis: "cost_value",
      rows: holdings.map((item) => ({
        symbol: item.symbol,
        name: item.name,
        weight: (item.cost_value ?? 0) / total,
      })),
    };
  }
  const quantityTotal = holdings.reduce((sum, item) => sum + item.quantity, 0);
  if (quantityTotal > 0) {
    return {
      basis: "quantity_share",
      rows: holdings.map((item) => ({
        symbol: item.symbol,
        name: item.name,
        weight: item.quantity / quantityTotal,
      })),
    };
  }
  return { basis: "insufficient_data", rows: [] };
}

function marketValueAllocation(
  holdings: Holding[],
  snapshots: MarketDataSnapshot[],
  mixedCurrency: boolean,
): { rows: AllocationRow[]; basis: WeightBasis } | null {
  if (mixedCurrency || snapshots.length === 0) {
    return null;
  }
  const prices = indexBySymbol(snapshots);
  const values: { holding: Holding; value: number }[] = [];
  for (const holding of holdings) {
    const price = prices.get(holding.symbol)?.current_price;
    if (price == null || price <= 0) {
      return null;
    }
    values.push({ holding, value: holding.quantity * price });
  }
  const total = values.reduce((sum, item) => sum + item.value, 0);
  if (total <= 0) {
    return null;
  }
  return {
    basis: "market_value",
    rows: values.map(({ holding, value }) => ({
      symbol: holding.symbol,
      name: holding.name,
      weight: value / total,
    })),
  };
}

function classifyConcentration(hhi: number | null, largest: number | null): ConcentrationLabel {
  const ranks: number[] = [];
  if (hhi != null) {
    ranks.push(hhi >= HHI_HIGH ? 2 : hhi >= HHI_LOW ? 1 : 0);
  }
  if (largest != null) {
    ranks.push(largest >= HIGH_CONCENTRATION_WEIGHT ? 2 : largest >= LARGE_POSITION_THRESHOLD ? 1 : 0);
  }
  if (!ranks.length) {
    return "insufficient_data";
  }
  const worst = Math.max(...ranks);
  if (worst >= 2) {
    return "high";
  }
  if (worst === 1) {
    return "moderate";
  }
  return "low";
}

function herfindahl(weights: number[]): number | null {
  if (!weights.length) {
    return null;
  }
  return weights.reduce((sum, weight) => sum + weight * weight, 0);
}

function indexBySymbol<T extends { symbol: string }>(items: T[]): Map<string, T> {
  return new Map(items.map((item) => [item.symbol, item]));
}

function portfolioLabel(item: PortfolioSummary): string {
  return item.name?.trim() || item.source_filename || "Untitled portfolio";
}

function stockPath(symbol: string): string {
  return `/stocks/${encodeURIComponent(symbol)}`;
}

function formatNumber(value: number | null | undefined, digits = 4): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function formatWeight(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return `${(value * 100).toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
}

function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return `${(value * 100).toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
}

function formatMoney(value: number | null | undefined, currency: string | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  const amount = value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return currency ? `${amount} ${currency}` : amount;
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
