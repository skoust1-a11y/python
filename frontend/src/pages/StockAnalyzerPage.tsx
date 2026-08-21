import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Brain,
  CircleAlert,
  Landmark,
  LineChart,
  Loader2,
  Search,
  Star,
} from "lucide-react";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, PageStatus } from "@/components";
import {
  getStock,
  getStockAnalysis,
  getStockFundamentals,
  getStockMarket,
  getSuggestedQuestions,
  listStockAnalyses,
  searchStocks,
  selectStock,
  submitStockAnalysis,
} from "@/api/stocks";
import { addWatchlistStock, getWatchlistStock } from "@/api/watchlist";
import { errorState, idleState, loadingState, successState, type AsyncState } from "@/lib/asyncState";
import { ApiError, toErrorMessage } from "@/models/errors";
import type {
  Evidence,
  FinalRecommendation,
  HistoricalPrice,
  InstrumentMatch,
  InvestmentHorizon,
  RiskTolerance,
  SpecialistResult,
  StockAnalysisResult,
  StockAnalysisSummary,
  StockFundamentalData,
  StockMarketData,
  StockOverview,
  SuggestedQuestion,
  WorkflowStatus,
  CritiqueRecord,
} from "@/models";

const SEARCH_DEBOUNCE_MS = 300;
const RISK_TOLERANCE_OPTIONS: RiskTolerance[] = ["conservative", "moderate", "aggressive"];
const HORIZON_OPTIONS: InvestmentHorizon[] = ["short", "medium", "long"];
const SYMBOL_PATTERN = /^\^?[A-Za-z0-9][A-Za-z0-9.\-]{0,31}$/;

export function StockAnalyzerPage() {
  const navigate = useNavigate();
  const { symbol: routeSymbol } = useParams();
  const symbol = normalizeRouteSymbol(routeSymbol);

  const [query, setQuery] = useState(symbol ?? "");
  const [debouncedQuery, setDebouncedQuery] = useState(symbol ?? "");
  const [country, setCountry] = useState<"IN" | "US" | "GLOBAL">("IN");
  const [search, setSearch] = useState<AsyncState<InstrumentMatch[]>>(idleState());
  const [selecting, setSelecting] = useState(false);
  const [selectionError, setSelectionError] = useState<unknown>(null);

  const [overview, setOverview] = useState<AsyncState<StockOverview>>(idleState());
  const [market, setMarket] = useState<AsyncState<StockMarketData>>(idleState());
  const [fundamentals, setFundamentals] = useState<AsyncState<StockFundamentalData>>(idleState());
  const [questions, setQuestions] = useState<SuggestedQuestion[]>([]);
  const [questionsError, setQuestionsError] = useState<unknown>(null);
  const [analyses, setAnalyses] = useState<StockAnalysisSummary[]>([]);
  const [result, setResult] = useState<StockAnalysisResult | null>(null);
  const [resultError, setResultError] = useState<unknown>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [loadingStored, setLoadingStored] = useState(false);
  const [searchHint, setSearchHint] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [riskTolerance, setRiskTolerance] = useState<RiskTolerance | "">("");
  const [horizon, setHorizon] = useState<InvestmentHorizon | "">("");
  const [onWatchlist, setOnWatchlist] = useState(false);
  const [watchlistBusy, setWatchlistBusy] = useState(false);
  const [watchlistMessage, setWatchlistMessage] = useState<string | null>(null);
  const [watchlistError, setWatchlistError] = useState<unknown>(null);
  const [reloadNonce, setReloadNonce] = useState(0);
  const searchRequest = useRef(0);
  const symbolRequest = useRef(0);
  const analysisRequest = useRef(0);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedQuery(query.trim()), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    if (!debouncedQuery) {
      setSearch(idleState());
      return;
    }
    const requestId = ++searchRequest.current;
    setSearch((current) => loadingState(current.data));
    void searchStocks(debouncedQuery, undefined, country)
      .then((response) => {
        if (searchRequest.current !== requestId) {
          return;
        }
        setSearch(successState(response.matches, response.matches.length === 0));
      })
      .catch((error) => {
        if (searchRequest.current === requestId) {
          setSearch(errorState(asError(error)));
        }
      });
  }, [debouncedQuery, country]);

  useEffect(() => {
    if (symbol) {
      setQuery(symbol);
      setDebouncedQuery(symbol);
    }
  }, [symbol]);

  useEffect(() => {
    if (!symbol) {
      ++analysisRequest.current;
      setOverview(idleState());
      setMarket(idleState());
      setFundamentals(idleState());
      setQuestions([]);
      setQuestionsError(null);
      setAnalyses([]);
      setResult(null);
      setResultError(null);
      setAnalyzing(false);
      setLoadingStored(false);
      setQuestion("");
      setSelectedPrompt(null);
      setOnWatchlist(false);
      setWatchlistMessage(null);
      setWatchlistError(null);
      setSearchHint(null);
      return;
    }
    const requestId = ++symbolRequest.current;
    ++analysisRequest.current;
    let cancelled = false;
    setOverview(loadingState());
    setMarket(loadingState());
    setFundamentals(loadingState());
    setQuestions([]);
    setQuestionsError(null);
    setAnalyses([]);
    setResult(null);
    setResultError(null);
    setAnalyzing(false);
    setLoadingStored(false);
    setQuestion("");
    setSelectedPrompt(null);
    setWatchlistMessage(null);
    setWatchlistError(null);
    setOnWatchlist(false);
    setSearchHint(null);

    async function loadSymbol(token: string) {
      const [overviewResult, marketResult, fundamentalResult, questionResult, analysisResult, watchlistResult] =
        await Promise.allSettled([
          getStock(token),
          getStockMarket(token),
          getStockFundamentals(token),
          getSuggestedQuestions(token),
          listStockAnalyses(token),
          getWatchlistStock(token),
        ]);
      if (cancelled || symbolRequest.current !== requestId) {
        return;
      }

      applySettled(overviewResult, setOverview);
      applySettled(marketResult, setMarket);
      applySettled(fundamentalResult, setFundamentals);

      if (questionResult.status === "fulfilled") {
        const items = questionResult.value.questions;
        setQuestions(items);
        if (items[0]) {
          setQuestion(items[0].question);
          setSelectedPrompt(items[0].id);
        }
      } else {
        setQuestionsError(questionResult.reason);
      }

      if (analysisResult.status === "fulfilled") {
        const history = analysisResult.value;
        setAnalyses(history);
        if (history[0]) {
          try {
            const latest = await getStockAnalysis(token, history[0].id);
            if (!cancelled && symbolRequest.current === requestId) {
              setResult(latest);
            }
          } catch (error) {
            if (!cancelled && symbolRequest.current === requestId) {
              setResultError(error);
            }
          }
        }
      }

      setOnWatchlist(watchlistResult.status === "fulfilled");
    }

    void loadSymbol(symbol);
    return () => {
      cancelled = true;
    };
  }, [symbol, reloadNonce]);

  const performance = useMemo(() => (market.data ? buildPerformance(market.data) : null), [market.data]);
  const retrievedEvidence = useMemo(
    () =>
      mergeEvidence(
        overview.data?.evidence ?? [],
        market.data?.evidence ?? [],
        fundamentals.data?.evidence ?? [],
      ),
    [overview.data, market.data, fundamentals.data],
  );

  async function chooseSymbol(token: string) {
    const candidate = token.trim();
    if (!candidate || selecting) {
      return;
    }
    setSelecting(true);
    setSelectionError(null);
    setSearchHint(null);
    try {
      const selected = await selectStock(candidate);
      navigate(stockPath(selected.symbol));
    } catch (error) {
      if (looksLikeSymbol(candidate)) {
        navigate(stockPath(candidate.toUpperCase()));
        return;
      }
      setSelectionError(error);
    } finally {
      setSelecting(false);
    }
  }

  function onSearchSubmit(event: FormEvent) {
    event.preventDefault();
    const token = query.trim();
    if (!token) {
      return;
    }
    setSearchHint(null);
    const matches = search.data ?? [];
    const exact = matches.find((item) => item.symbol.toUpperCase() === token.toUpperCase());
    if (exact) {
      void chooseSymbol(exact.symbol);
      return;
    }
    if (matches.length === 1) {
      void chooseSymbol(matches[0].symbol);
      return;
    }
    if (looksLikeSymbol(token)) {
      void chooseSymbol(token);
      return;
    }
    if (matches.length > 1) {
      setSearchHint("Select an instrument from the results to open it in Stock Analyzer.");
      return;
    }
    setSearchHint("No instrument matched that search. Try a ticker symbol or a listed company name.");
  }

  function applyPrompt(prompt: SuggestedQuestion) {
    setSelectedPrompt(prompt.id);
    setQuestion(prompt.question);
  }

  function onQuestionChange(value: string) {
    setQuestion(value);
    const match = questions.find((item) => item.question === value);
    setSelectedPrompt(match?.id ?? null);
  }

  async function runAnalysis(event: FormEvent) {
    event.preventDefault();
    if (!symbol || analyzing || loadingStored) {
      return;
    }
    const text = question.trim();
    if (!text) {
      return;
    }
    setAnalyzing(true);
    setResultError(null);
    const requestId = ++analysisRequest.current;
    try {
      const analysis = await submitStockAnalysis(symbol, {
        question: text,
        analysis_type: "stock_analysis",
        risk_tolerance: riskTolerance || null,
        horizon: horizon || null,
      });
      if (analysisRequest.current !== requestId) {
        return;
      }
      setResult(analysis);
      setAnalyses((current) => [
        {
          id: analysis.id,
          symbol: analysis.symbol,
          question: analysis.question,
          analysis_type: analysis.analysis_type,
          status: analysis.status,
          created_at: analysis.created_at,
        },
        ...current.filter((item) => item.id !== analysis.id),
      ]);
    } catch (error) {
      if (analysisRequest.current === requestId) {
        setResultError(error);
      }
    } finally {
      if (analysisRequest.current === requestId) {
        setAnalyzing(false);
      }
    }
  }

  async function openStoredAnalysis(analysisId: string) {
    if (!symbol || analyzing || loadingStored) {
      return;
    }
    setLoadingStored(true);
    setResultError(null);
    const requestId = ++analysisRequest.current;
    try {
      const analysis = await getStockAnalysis(symbol, analysisId);
      if (analysisRequest.current !== requestId) {
        return;
      }
      setResult(analysis);
      setQuestion(analysis.question);
      const match = questions.find((item) => item.question === analysis.question);
      setSelectedPrompt(match?.id ?? null);
    } catch (error) {
      if (analysisRequest.current === requestId) {
        setResultError(error);
      }
    } finally {
      if (analysisRequest.current === requestId) {
        setLoadingStored(false);
      }
    }
  }

  async function addToWatchlist() {
    if (!symbol || watchlistBusy || onWatchlist) {
      return;
    }
    setWatchlistBusy(true);
    setWatchlistError(null);
    setWatchlistMessage(null);
    try {
      await addWatchlistStock(symbol);
      setOnWatchlist(true);
      setWatchlistMessage(`${symbol} was added to Watchlist. Monitoring stays on that screen; analysis stays here.`);
    } catch (error) {
      if (error instanceof ApiError && error.code === "conflict") {
        setOnWatchlist(true);
        setWatchlistMessage(`${symbol} is already on Watchlist.`);
        return;
      }
      setWatchlistError(error);
    } finally {
      setWatchlistBusy(false);
    }
  }

  const title = symbol ? `Stock Analyzer · ${symbol}` : "Stock Analyzer";
  const displayName = overview.data?.name ?? overview.data?.selected.name ?? null;

  return (
    <>
      <PageHeader
        title={title}
        description="Search, select, and analyze a single instrument. This screen does not use an uploaded portfolio unless you go to Portfolio Analyzer for book-level questions."
        actions={
          symbol ? (
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="secondary" onClick={() => navigate("/stocks")}>
                New search
              </Button>
              <Button
                variant={onWatchlist ? "secondary" : "primary"}
                onClick={() => {
                  if (onWatchlist) {
                    navigate("/watchlist");
                    return;
                  }
                  void addToWatchlist();
                }}
                disabled={watchlistBusy}
              >
                {watchlistBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Star className="h-4 w-4" />}
                {onWatchlist ? "Open Watchlist" : "Add to Watchlist"}
              </Button>
            </div>
          ) : null
        }
      />

      <div className="space-y-4">
        <SearchCard
          query={query}
          country={country}
          search={search}
          selecting={selecting}
          selectionError={selectionError}
          searchHint={searchHint}
          activeSymbol={symbol}
          onQueryChange={(value) => {
            setQuery(value);
            setSearchHint(null);
          }}
          onCountryChange={(val) => {
            setCountry(val);
            setSearchHint(null);
          }}
          onSubmit={onSearchSubmit}
          onSelect={(match) => void chooseSymbol(match.symbol)}
          onOpenTicker={() => void chooseSymbol(query)}
        />

        {!symbol ? (
          <PageStatus
            empty
            emptyTitle="No stock selected"
            emptyDescription="Search for a ticker or company name, then select an instrument. Market data, fundamentals, suggested questions, and AI analysis appear after selection."
          />
        ) : (
          <>
            <CompositionBanner symbol={symbol} name={displayName} />
            <IdentityCard
              symbol={symbol}
              overview={overview}
              onWatchlist={onWatchlist}
              watchlistBusy={watchlistBusy}
              watchlistMessage={watchlistMessage}
              watchlistError={watchlistError}
              onWatchlistAction={() => {
                if (onWatchlist) {
                  navigate("/watchlist");
                  return;
                }
                void addToWatchlist();
              }}
              onRetry={() => setReloadNonce((value) => value + 1)}
            />
            <div className="grid gap-4 lg:grid-cols-2">
              <MarketCard state={market} onRetry={() => setReloadNonce((value) => value + 1)} />
              <PerformanceCard
                state={market}
                performance={performance}
                onRetry={() => setReloadNonce((value) => value + 1)}
              />
            </div>
            <FundamentalsCard state={fundamentals} onRetry={() => setReloadNonce((value) => value + 1)} />
            {retrievedEvidence.length ? <RetrievedSourcesCard evidence={retrievedEvidence} /> : null}
            <AskCard
              symbol={symbol}
              question={question}
              selectedPrompt={selectedPrompt}
              questions={questions}
              questionsError={questionsError}
              riskTolerance={riskTolerance}
              horizon={horizon}
              analyzing={analyzing}
              locked={loadingStored}
              onQuestionChange={onQuestionChange}
              onSelectPrompt={applyPrompt}
              onRiskToleranceChange={setRiskTolerance}
              onHorizonChange={setHorizon}
              onSubmit={runAnalysis}
            />
            {analyses.length ? (
              <PriorRuns analyses={analyses} activeId={result?.id ?? null} onOpen={openStoredAnalysis} />
            ) : null}
            <AnalysisOutput
              analyzing={analyzing}
              loadingStored={loadingStored}
              error={resultError}
              result={result}
            />
          </>
        )}
      </div>
    </>
  );
}

function SearchCard({
  query,
  country,
  search,
  selecting,
  selectionError,
  searchHint,
  activeSymbol,
  onQueryChange,
  onCountryChange,
  onSubmit,
  onSelect,
  onOpenTicker,
}: {
  query: string;
  country: "IN" | "US" | "GLOBAL";
  search: AsyncState<InstrumentMatch[]>;
  selecting: boolean;
  selectionError: unknown;
  searchHint: string | null;
  activeSymbol: string | null;
  onQueryChange: (value: string) => void;
  onCountryChange: (value: "IN" | "US" | "GLOBAL") => void;
  onSubmit: (event: FormEvent) => void;
  onSelect: (match: InstrumentMatch) => void;
  onOpenTicker: () => void;
}) {
  const matches = search.data ?? [];
  return (
    <Card title="Stock search">
      <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={onSubmit}>
        <label className="block w-full sm:w-48 text-sm">
          <span className="font-medium text-slate-700">Market / Country</span>
          <select
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-600"
            value={country}
            onChange={(event) => onCountryChange(event.target.value as "IN" | "US" | "GLOBAL")}
            disabled={selecting}
          >
            <option value="IN">🇮🇳 India (NSE / BSE)</option>
            <option value="US">🇺🇸 US (NYSE / NASDAQ)</option>
            <option value="GLOBAL">🌐 Global Markets</option>
          </select>
        </label>
        <label className="block flex-1 text-sm">
          <span className="font-medium text-slate-700">Ticker, company name, or idea</span>
          <input
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-600"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder={
              country === "IN"
                ? "Search Reliance, TCS, Tata Motors, or theme (e.g. EV, Solar)..."
                : country === "US"
                ? "Search AAPL, Microsoft, Tesla..."
                : "Search AAPL, Reliance, or another listed name"
            }
            maxLength={64}
            autoComplete="off"
            disabled={selecting}
          />
        </label>
        <div className="flex items-end">
          <Button type="submit" disabled={!query.trim() || selecting}>
            {selecting || search.status === "loading" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            {selecting ? "Selecting..." : "Search"}
          </Button>
        </div>
      </form>
      {search.status === "error" ? (
        <div className="mt-3 text-sm text-amber-800">
          <p>
            {toErrorMessage(search.error)}. You can still open a ticker if you already know the symbol.
          </p>
          {looksLikeSymbol(query) ? (
            <Button className="mt-2" variant="secondary" onClick={onOpenTicker} disabled={selecting}>
              Open {query.trim().toUpperCase()}
            </Button>
          ) : null}
        </div>
      ) : null}
      {selectionError ? (
        <p className="mt-3 text-sm text-red-700">{toErrorMessage(selectionError)}</p>
      ) : null}
      {searchHint ? <p className="mt-3 text-sm text-slate-600">{searchHint}</p> : null}
      {search.status === "empty" ? (
        <p className="mt-3 text-sm text-slate-500">No instruments matched “{query.trim()}”.</p>
      ) : null}
      {matches.length > 1 ? (
        <p className="mt-3 text-xs text-slate-500">Select an instrument below to open it in Stock Analyzer.</p>
      ) : null}
      {matches.length ? (
        <ul className="mt-3 divide-y divide-slate-100 rounded-md border border-slate-200">
          {matches.map((match) => {
            const active = match.symbol === activeSymbol;
            return (
              <li key={`${match.symbol}-${match.exchange ?? ""}`}>
                <button
                  type="button"
                  className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm ${
                    active ? "bg-brand-50 text-brand-800" : "hover:bg-slate-50"
                  }`}
                  onClick={() => onSelect(match)}
                  disabled={selecting}
                >
                  <span>
                    <span className="font-medium text-slate-900">{match.symbol}</span>
                    <span className="mt-0.5 block text-xs text-slate-500">
                      {match.name ?? "Unnamed instrument"}
                      {match.exchange ? ` · ${match.exchange}` : ""}
                      {match.currency ? ` · ${match.currency}` : ""}
                    </span>
                  </span>
                  <span className="text-xs font-medium text-brand-700">{active ? "Selected" : "Select"}</span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </Card>
  );
}

function CompositionBanner({ symbol, name }: { symbol: string; name: string | null }) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">What this analysis uses</p>
      <p className="mt-1 text-sm font-medium text-slate-900">
        Current market and fundamental information for {name ?? symbol} + AI specialist analysis
      </p>
      <p className="mt-1 text-xs text-slate-500">
        Independent of any uploaded portfolio. Book-level questions belong on Portfolio Analyzer.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <CompositionStep
          icon={<LineChart className="h-4 w-4" />}
          title="Current market"
          body="Quote, volume, history, trend, and related performance from the configured market adapter. Missing fields stay missing."
        />
        <CompositionStep
          icon={<Landmark className="h-4 w-4" />}
          title="Fundamentals"
          body="Company profile, reported metrics, and valuation retrieved at request time. Figures are not invented."
        />
        <CompositionStep
          icon={<Brain className="h-4 w-4" />}
          title="AI specialists"
          body="Market, fundamental, and risk agents interpret retrieved evidence for this single name. Trades are not executed."
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

function IdentityCard({
  symbol,
  overview,
  onWatchlist,
  watchlistBusy,
  watchlistMessage,
  watchlistError,
  onWatchlistAction,
  onRetry,
}: {
  symbol: string;
  overview: AsyncState<StockOverview>;
  onWatchlist: boolean;
  watchlistBusy: boolean;
  watchlistMessage: string | null;
  watchlistError: unknown;
  onWatchlistAction: () => void;
  onRetry: () => void;
}) {
  const data = overview.data;
  const quote = data?.quote ?? null;
  return (
    <Card
      title="Selected stock"
      action={
        <Button
          variant={onWatchlist ? "secondary" : "primary"}
          onClick={onWatchlistAction}
          disabled={watchlistBusy}
        >
          {watchlistBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Star className="h-4 w-4" />}
          {onWatchlist ? "Open Watchlist" : "Add to Watchlist"}
        </Button>
      }
    >
      {overview.status === "loading" || overview.status === "idle" ? (
        <PanelLoading label="Loading current information..." />
      ) : overview.status === "error" && !data ? (
        <ErrorState error={overview.error} title="Current information could not be loaded" onRetry={onRetry} />
      ) : (
        <>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-lg font-semibold text-slate-900">{data?.name ?? symbol}</p>
              <p className="text-sm text-slate-500">
                {symbol}
                {data?.exchange ? ` · ${data.exchange}` : ""}
                {data?.currency ? ` · ${data.currency}` : ""}
                {data?.asset_class ? ` · ${data.asset_class}` : ""}
              </p>
            </div>
            <div className="text-right">
              <p className="text-lg font-semibold tabular-nums text-slate-900">
                {formatMoney(quote?.value ?? null, data?.currency ?? quote?.currency)}
              </p>
              <p className={`text-sm tabular-nums ${signedClass(quote?.change_percent ?? quote?.change)}`}>
                {formatSignedChange(quote?.change, quote?.change_percent, data?.currency ?? quote?.currency)}
              </p>
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Add to Watchlist keeps you on this screen until you open Watchlist. Watchlist monitors the symbol and
            does not run AI analysis.
            {onWatchlist ? (
              <>
                {" "}
                <Link className="font-medium text-brand-700 hover:underline" to="/watchlist">
                  Open Watchlist
                </Link>
              </>
            ) : null}
          </p>
          {watchlistMessage ? <p className="mt-2 text-sm text-emerald-800">{watchlistMessage}</p> : null}
          {watchlistError ? <p className="mt-2 text-sm text-red-700">{toErrorMessage(watchlistError)}</p> : null}
          {data?.unavailable.length ? <UnavailableNote fields={data.unavailable} /> : null}
        </>
      )}
    </Card>
  );
}

function MarketCard({
  state,
  onRetry,
}: {
  state: AsyncState<StockMarketData>;
  onRetry: () => void;
}) {
  const data = state.data;
  const quote = data?.quote ?? null;
  const volume = data?.volume ?? null;
  const info = data?.market_info ?? null;
  const snapshot = data?.snapshot ?? null;
  return (
    <Card title="Current market information">
      <PanelStatus
        loading={state.status === "loading" || state.status === "idle"}
        loadingLabel="Loading market data..."
        error={state.status === "error" ? state.error : undefined}
        errorTitle="Market data could not be retrieved"
        onRetry={onRetry}
        empty={state.status === "success" && !quote && !volume && !info}
        emptyTitle="No market data"
        emptyDescription="The configured market adapter did not return a quote, volume, or market info for this symbol."
      >
        {data ? (
          <>
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <Metric label="Last price" value={formatMoney(quote?.value ?? snapshot?.current_price, snapshot?.currency ?? quote?.currency)} />
              <Metric label="Change" value={formatSignedChange(quote?.change, quote?.change_percent, quote?.currency)} />
              <Metric label="Bid / ask" value={formatBidAsk(quote?.bid, quote?.ask, quote?.currency)} />
              <Metric label="Volume" value={formatCompact(volume?.value ?? snapshot?.volume ?? quote?.volume)} />
              <Metric label="Average volume" value={formatCompact(volume?.average_volume)} />
              <Metric label="Exchange" value={snapshot?.exchange ?? info?.exchange ?? quote?.exchange ?? "—"} />
              <Metric label="Asset class" value={info?.asset_class ?? "—"} />
              <Metric label="As of" value={formatDate(quote?.timestamp ?? snapshot?.as_of)} />
              <Metric label="Timezone" value={info?.timezone ?? "—"} />
              <Metric label="Trading hours" value={info?.trading_hours ?? "—"} />
            </dl>
            <SourceLine source={quote?.source ?? info?.source ?? snapshot?.source ?? null} />
            {data.unavailable.length ? <UnavailableNote fields={data.unavailable} /> : null}
          </>
        ) : null}
      </PanelStatus>
    </Card>
  );
}

function PerformanceCard({
  state,
  performance,
  onRetry,
}: {
  state: AsyncState<StockMarketData>;
  performance: PerformanceView | null;
  onRetry: () => void;
}) {
  const snapshot = state.data?.snapshot ?? null;
  return (
    <Card title="Relevant performance">
      <PanelStatus
        loading={state.status === "loading" || state.status === "idle"}
        loadingLabel="Loading performance series..."
        error={state.status === "error" ? state.error : undefined}
        errorTitle="Performance data could not be retrieved"
        onRetry={onRetry}
        empty={state.status === "success" && !performance?.closes.length && !snapshot?.trend}
        emptyTitle="No performance series"
        emptyDescription="Trend, volatility, and period return need retrieved history. Missing bars are not filled in."
      >
        {state.data ? (
          <>
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <Metric label="Trend" value={snapshot?.trend ?? "—"} />
              <Metric label="Volatility" value={formatPercent(snapshot?.volatility)} />
              <Metric label="Momentum" value={formatPercent(snapshot?.momentum)} />
              <Metric label="Period return" value={formatPercent(performance?.periodReturn ?? null)} />
              <Metric label="Period high" value={formatMoney(performance?.high ?? null, snapshot?.currency)} />
              <Metric label="Period low" value={formatMoney(performance?.low ?? null, snapshot?.currency)} />
              <Metric label="Bars" value={performance?.barCount ? String(performance.barCount) : "—"} />
              <Metric label="Interval" value={performance?.period ?? "—"} />
            </dl>
            {performance?.closes.length ? (
              <div className="mt-4">
                <Sparkline values={performance.closes} />
                <p className="mt-2 text-xs text-slate-500">
                  Closing prices from retrieved history
                  {performance.start ? ` · ${formatDate(performance.start)}` : ""}
                  {performance.end ? ` – ${formatDate(performance.end)}` : ""}.
                </p>
              </div>
            ) : null}
            {performance?.recent.length ? (
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-left text-xs">
                  <thead className="border-b border-slate-200 text-slate-500">
                    <tr>
                      <th className="px-2 py-1 font-medium">Date</th>
                      <th className="px-2 py-1 font-medium">Close</th>
                      <th className="px-2 py-1 font-medium">High</th>
                      <th className="px-2 py-1 font-medium">Low</th>
                      <th className="px-2 py-1 font-medium">Volume</th>
                    </tr>
                  </thead>
                  <tbody>
                    {performance.recent.map((bar) => (
                      <tr key={bar.timestamp} className="border-b border-slate-100">
                        <td className="px-2 py-1">{formatDate(bar.timestamp)}</td>
                        <td className="px-2 py-1 tabular-nums">{formatMoney(bar.close, bar.currency)}</td>
                        <td className="px-2 py-1 tabular-nums">{formatMoney(bar.high, bar.currency)}</td>
                        <td className="px-2 py-1 tabular-nums">{formatMoney(bar.low, bar.currency)}</td>
                        <td className="px-2 py-1 tabular-nums">{formatCompact(bar.volume)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </>
        ) : null}
      </PanelStatus>
    </Card>
  );
}

function FundamentalsCard({
  state,
  onRetry,
}: {
  state: AsyncState<StockFundamentalData>;
  onRetry: () => void;
}) {
  const data = state.data;
  const profile = data?.profile ?? null;
  const metrics = data?.metrics ?? null;
  const valuation = data?.valuation ?? null;
  const snapshot = data?.snapshot ?? null;
  return (
    <Card title="Fundamental information">
      <PanelStatus
        loading={state.status === "loading" || state.status === "idle"}
        loadingLabel="Loading fundamentals..."
        error={state.status === "error" ? state.error : undefined}
        errorTitle="Fundamentals could not be retrieved"
        onRetry={onRetry}
        empty={state.status === "success" && !profile && !metrics && !valuation}
        emptyTitle="No fundamental data"
        emptyDescription="The configured fundamental adapter did not return a profile, metrics, or valuation for this symbol."
      >
        {data ? (
          <div className="space-y-4">
            <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <Metric label="Company" value={snapshot?.company_name ?? profile?.name ?? "—"} />
              <Metric label="Sector" value={snapshot?.sector ?? profile?.sector ?? "—"} />
              <Metric label="Industry" value={snapshot?.industry ?? profile?.industry ?? "—"} />
              <Metric label="Country" value={profile?.country ?? "—"} />
              <Metric label="Profitability" value={snapshot?.profitability ?? "—"} />
              <Metric label="Financial health" value={snapshot?.financial_health ?? "—"} />
              <Metric label="Employees" value={formatCompact(profile?.employees ?? null)} />
              <Metric
                label="Website"
                value={
                  profile?.website ? (
                    <a className="text-brand-700 hover:underline" href={profile.website} target="_blank" rel="noreferrer">
                      {profile.website}
                    </a>
                  ) : (
                    "—"
                  )
                }
              />
            </dl>
            {profile?.description ? (
              <p className="text-sm leading-6 text-slate-600">{profile.description}</p>
            ) : null}
            <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <Metric label="Revenue" value={formatCompactMoney(snapshot?.revenue ?? metrics?.revenue, metrics?.currency)} />
              <Metric
                label="Earnings"
                value={formatCompactMoney(snapshot?.earnings ?? metrics?.net_income, metrics?.currency)}
              />
              <Metric label="EPS" value={formatNumber(metrics?.eps)} />
              <Metric label="EBITDA" value={formatCompactMoney(metrics?.ebitda, metrics?.currency)} />
              <Metric label="Operating margin" value={formatRatioOrPercent(metrics?.operating_margin)} />
              <Metric label="Profit margin" value={formatRatioOrPercent(metrics?.profit_margin)} />
              <Metric label="ROE" value={formatRatioOrPercent(metrics?.roe)} />
              <Metric label="ROA" value={formatRatioOrPercent(metrics?.roa)} />
              <Metric label="Debt / equity" value={formatNumber(metrics?.debt_to_equity)} />
              <Metric label="Current ratio" value={formatNumber(metrics?.current_ratio)} />
              <Metric
                label="P/E"
                value={formatNumber(snapshot?.pe_ratio ?? valuation?.pe_ratio ?? metrics?.pe_ratio)}
              />
              <Metric label="Forward P/E" value={formatNumber(valuation?.forward_pe ?? metrics?.forward_pe)} />
              <Metric label="P/B" value={formatNumber(valuation?.pb_ratio ?? metrics?.pb_ratio)} />
              <Metric label="P/S" value={formatNumber(valuation?.ps_ratio ?? metrics?.ps_ratio)} />
              <Metric label="PEG" value={formatNumber(valuation?.peg_ratio ?? metrics?.peg_ratio)} />
              <Metric label="EV / EBITDA" value={formatNumber(valuation?.ev_to_ebitda ?? metrics?.ev_to_ebitda)} />
              <Metric
                label="Market cap"
                value={formatCompactMoney(valuation?.market_cap ?? metrics?.market_cap, valuation?.currency ?? metrics?.currency)}
              />
              <Metric
                label="Dividend yield"
                value={formatRatioOrPercent(valuation?.dividend_yield ?? metrics?.dividend_yield)}
              />
            </dl>
            <SourceLine source={profile?.source ?? metrics?.source ?? valuation?.source ?? snapshot?.source ?? null} />
            {data.unavailable.length ? <UnavailableNote fields={data.unavailable} /> : null}
          </div>
        ) : null}
      </PanelStatus>
    </Card>
  );
}

function RetrievedSourcesCard({ evidence }: { evidence: Evidence[] }) {
  return (
    <Card title="Retrieved sources">
      <p className="text-sm text-slate-600">
        Market and fundamental figures below come from configured providers. Values are not invented when a source is
        missing.
      </p>
      <EvidenceList evidence={evidence} />
    </Card>
  );
}

function AskCard({
  symbol,
  question,
  selectedPrompt,
  questions,
  questionsError,
  riskTolerance,
  horizon,
  analyzing,
  locked,
  onQuestionChange,
  onSelectPrompt,
  onRiskToleranceChange,
  onHorizonChange,
  onSubmit,
}: {
  symbol: string;
  question: string;
  selectedPrompt: string | null;
  questions: SuggestedQuestion[];
  questionsError: unknown;
  riskTolerance: RiskTolerance | "";
  horizon: InvestmentHorizon | "";
  analyzing: boolean;
  locked: boolean;
  onQuestionChange: (value: string) => void;
  onSelectPrompt: (prompt: SuggestedQuestion) => void;
  onRiskToleranceChange: (value: RiskTolerance | "") => void;
  onHorizonChange: (value: InvestmentHorizon | "") => void;
  onSubmit: (event: FormEvent) => void;
}) {
  const busy = analyzing || locked;
  const canSubmit = question.trim().length > 0 && !busy;
  return (
    <Card title="Ask about this stock">
      <form className="space-y-4" onSubmit={onSubmit}>
        <div>
          <p className="text-sm font-medium text-slate-700">Suggested questions</p>
          {questionsError ? (
            <p className="mt-2 text-sm text-amber-800">{toErrorMessage(questionsError)}</p>
          ) : null}
          {questions.length ? (
            <ul className="mt-2 flex flex-wrap gap-2">
              {questions.map((prompt) => {
                const active = selectedPrompt === prompt.id;
                return (
                  <li key={prompt.id}>
                    <button
                      type="button"
                      className={`rounded-full px-3 py-1.5 text-left text-xs font-medium ${
                        active ? "bg-brand-700 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                      }`}
                      onClick={() => onSelectPrompt(prompt)}
                      disabled={busy}
                    >
                      {prompt.question}
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : !questionsError ? (
            <p className="mt-2 text-sm text-slate-500">Suggested questions are not available yet.</p>
          ) : null}
        </div>

        <label className="block text-sm">
          <span className="font-medium text-slate-700">Custom question</span>
          <textarea
            className="mt-1 min-h-[96px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-600"
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            placeholder={`Ask about ${symbol}'s trend, valuation, or risks using retrieved evidence.`}
            maxLength={2000}
            disabled={busy}
          />
        </label>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Risk tolerance</span>
            <select
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-600"
              value={riskTolerance}
              onChange={(event) => onRiskToleranceChange(event.target.value as RiskTolerance | "")}
              disabled={busy}
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
              disabled={busy}
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
            {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
            {analyzing ? "Running analysis..." : "Run AI analysis"}
          </Button>
          <p className="text-xs text-slate-500">
            Runs single-stock analysis only. No portfolio rebalancing, and no trades are placed.
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
  analyses: StockAnalysisSummary[];
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
  loadingStored,
  error,
  result,
}: {
  analyzing: boolean;
  loadingStored: boolean;
  error: unknown;
  result: StockAnalysisResult | null;
}) {
  if (analyzing) {
    return (
      <div className="rounded-lg border border-brand-100 bg-brand-50 px-4 py-8" role="status" aria-live="polite">
        <LoadingState label="Specialists are analyzing this stock with current market and fundamental data..." />
      </div>
    );
  }
  if (loadingStored) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white px-4 py-8" role="status" aria-live="polite">
        <LoadingState label="Loading the stored structured report..." />
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
        description="Choose a suggested question or write your own, then run AI analysis. The structured report, recommendation, and evidence will appear here."
      />
    );
  }
  return <AnalysisReport result={result} />;
}

function AnalysisReport({ result }: { result: StockAnalysisResult }) {
  const recommendation = result.recommendation;
  const market = result.market_data[0] ?? null;
  const fundamental = result.fundamental_data[0] ?? null;
  const risk = result.risk_analysis;
  return (
    <div className="space-y-4">
      <Card title="Structured AI report">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={result.status} />
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
            Stock analysis · {result.symbol}
          </span>
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
          <Metric label="Specialists invoked" value={result.execution.invoked_agents.join(", ") || "—"} />
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

      {(market || fundamental) && (
        <Card title="Analysis snapshots">
          <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Price" value={formatMoney(market?.current_price ?? null, market?.currency)} />
            <Metric label="Trend" value={market?.trend ?? "—"} />
            <Metric label="Volatility" value={formatPercent(market?.volatility)} />
            <Metric label="Momentum" value={formatPercent(market?.momentum)} />
            <Metric label="Profitability" value={fundamental?.profitability ?? "—"} />
            <Metric label="Financial health" value={fundamental?.financial_health ?? "—"} />
            <Metric label="P/E" value={formatNumber(fundamental?.pe_ratio)} />
            <Metric label="Overall risk" value={risk?.overall_risk_assessment ?? "—"} />
          </dl>
        </Card>
      )}

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

      {risk?.major_risks.length ? (
        <Card title="Risk notes">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
            {risk.major_risks.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {risk.unavailable.length ? (
            <p className="mt-3 text-sm text-amber-800">Unavailable risk fields: {risk.unavailable.join(", ")}.</p>
          ) : null}
        </Card>
      ) : null}

      {result.news.length ? (
        <Card title="News used">
          <ul className="space-y-2 text-sm">
            {result.news.map((item, index) => (
              <li key={`${item.headline}-${index}`} className="rounded-md border border-slate-200 px-3 py-2">
                <p className="font-medium text-slate-800">{item.headline}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {item.publisher ?? item.source.provider} · {formatDate(item.timestamp)}
                  {item.url ? (
                    <>
                      {" · "}
                      <a className="text-brand-700 hover:underline" href={item.url} target="_blank" rel="noreferrer">
                        Source link
                      </a>
                    </>
                  ) : null}
                </p>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <RecommendationCard recommendation={recommendation} />
      <Card title="Evidence and sources">
        <p className="text-sm text-slate-600">
          Retrieved from configured market and fundamental providers during this run. Values are not invented when a
          source is missing.
        </p>
        <EvidenceList evidence={result.evidence} />
      </Card>
      <LimitationsCard recommendation={recommendation} />
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
      {result.error_message ? <p className="mt-2 text-sm text-red-700">{result.error_message}</p> : null}
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
            Confidence {recommendation.confidence == null ? "—" : formatWeight(recommendation.confidence)} · Trade
            execution {recommendation.trade_execution.replace("_", " ")}
          </p>
        </div>
      )}
    </Card>
  );
}

function LimitationsCard({ recommendation }: { recommendation: FinalRecommendation | null }) {
  const assumptions = recommendation?.assumptions ?? [];
  const limitations = recommendation?.limitations ?? [];
  return (
    <Card title="Limitations and assumptions">
      {!assumptions.length && !limitations.length ? (
        <p className="text-sm text-slate-500">
          No explicit limitations were returned. Analysis still depends on retrieved snapshots and specialist
          interpretation. Missing market or fundamental fields are not filled in. This report is not a portfolio
          recommendation.
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
            {limitations.length ? (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-700">
                {limitations.map((item) => (
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

function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) {
    return <p className="mt-3 text-sm text-slate-500">No evidence items were attached.</p>;
  }
  return (
    <ul className="mt-3 space-y-2">
      {evidence.map((item, index) => (
        <li
          key={`${item.source.provider}-${item.symbol}-${item.field}-${index}`}
          className="rounded-md border border-slate-200 px-3 py-2 text-sm"
        >
          <p className="font-medium text-slate-800">
            {item.symbol ?? "Instrument"}
            {item.field ? ` · ${item.field}` : ""}
            {item.value != null ? ` · ${String(item.value)}` : ""}
          </p>
          {item.excerpt ? <p className="mt-1 text-slate-600">{item.excerpt}</p> : null}
          <p className="mt-1 text-xs text-slate-500">
            {item.source.provider} · {item.source.source} · {formatDate(item.source.timestamp)}
            {item.period ? ` · ${item.period}` : ""}
            {item.source.url ? (
              <>
                {" · "}
                <a className="text-brand-700 hover:underline" href={item.source.url} target="_blank" rel="noreferrer">
                  Source link
                </a>
              </>
            ) : null}
          </p>
        </li>
      ))}
    </ul>
  );
}

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) {
    return null;
  }
  const width = 320;
  const height = 72;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");
  const up = values[values.length - 1] >= values[0];
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={`h-20 w-full ${up ? "text-emerald-600" : "text-red-600"}`}
      role="img"
      aria-label="Closing-price history"
    >
      <polyline fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" points={points} />
    </svg>
  );
}

function PanelStatus({
  loading = false,
  loadingLabel = "Loading...",
  error,
  errorTitle,
  onRetry,
  empty = false,
  emptyTitle,
  emptyDescription,
  children,
}: {
  loading?: boolean;
  loadingLabel?: string;
  error?: unknown;
  errorTitle?: string;
  onRetry?: () => void;
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  children?: ReactNode;
}) {
  if (loading) {
    return <PanelLoading label={loadingLabel} />;
  }
  if (error) {
    return <ErrorState error={error} title={errorTitle} onRetry={onRetry} />;
  }
  if (empty) {
    return (
      <div>
        <p className="text-sm font-medium text-slate-800">{emptyTitle}</p>
        {emptyDescription ? <p className="mt-1 text-sm text-slate-500">{emptyDescription}</p> : null}
      </div>
    );
  }
  return <>{children}</>;
}

function PanelLoading({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 py-3 text-sm text-slate-500" role="status" aria-live="polite">
      <Loader2 className="h-4 w-4 animate-spin text-brand-700" />
      {label}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
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
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}>{status}</span>;
}

function UnavailableNote({ fields }: { fields: string[] }) {
  return (
    <p className="mt-3 text-sm text-amber-800">
      Unavailable: {fields.map(humanizeField).join(", ")}. These fields were not invented.
    </p>
  );
}

function SourceLine({
  source,
}: {
  source: { provider: string; source: string; timestamp: string; url: string | null } | null;
}) {
  if (!source) {
    return null;
  }
  return (
    <p className="mt-3 text-xs text-slate-500">
      Source: {source.provider} · {source.source} · {formatDate(source.timestamp)}
      {source.url ? (
        <>
          {" · "}
          <a className="text-brand-700 hover:underline" href={source.url} target="_blank" rel="noreferrer">
            Source link
          </a>
        </>
      ) : null}
    </p>
  );
}

interface PerformanceView {
  closes: number[];
  recent: HistoricalPrice[];
  periodReturn: number | null;
  high: number | null;
  low: number | null;
  barCount: number;
  period: string | null;
  start: string | null;
  end: string | null;
}

function buildPerformance(market: StockMarketData): PerformanceView {
  const bars = [...(market.history?.prices ?? [])].sort(
    (left, right) => new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime(),
  );
  const closes = bars.map((bar) => bar.close);
  const first = closes[0];
  const last = closes[closes.length - 1];
  return {
    closes,
    recent: bars.slice(-5).reverse(),
    periodReturn: first && last && first !== 0 ? last / first - 1 : null,
    high: bars.length ? Math.max(...bars.map((bar) => bar.high)) : null,
    low: bars.length ? Math.min(...bars.map((bar) => bar.low)) : null,
    barCount: bars.length,
    period: market.history?.period ?? null,
    start: market.history?.start ?? bars[0]?.timestamp ?? null,
    end: market.history?.end ?? bars[bars.length - 1]?.timestamp ?? null,
  };
}

function mergeEvidence(...groups: Evidence[][]): Evidence[] {
  const seen = new Set<string>();
  const merged: Evidence[] = [];
  for (const group of groups) {
    for (const item of group) {
      const key = `${item.source.provider}|${item.source.source}|${item.symbol}|${item.field}|${String(item.value)}|${item.period}`;
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      merged.push(item);
    }
  }
  return merged;
}

function applySettled<T>(
  result: PromiseSettledResult<T>,
  setState: (state: AsyncState<T>) => void,
) {
  if (result.status === "fulfilled") {
    setState(successState(result.value));
    return;
  }
  setState(errorState(asError(result.reason)));
}

function normalizeRouteSymbol(value: string | undefined): string | null {
  const token = value?.trim();
  if (!token) {
    return null;
  }
  try {
    return decodeURIComponent(token).toUpperCase();
  } catch {
    return token.toUpperCase();
  }
}

function looksLikeSymbol(value: string): boolean {
  return SYMBOL_PATTERN.test(value.trim());
}

function stockPath(symbol: string): string {
  return `/stocks/${encodeURIComponent(symbol)}`;
}

function humanizeField(field: string): string {
  return field.replaceAll("_", " ");
}

function signedClass(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value) || value === 0) {
    return "text-slate-500";
  }
  return value > 0 ? "text-emerald-700" : "text-red-700";
}

function formatSignedChange(
  change: number | null | undefined,
  changePercent: number | null | undefined,
  currency: string | null | undefined,
): string {
  if (change == null && changePercent == null) {
    return "—";
  }
  const parts: string[] = [];
  if (change != null) {
    const sign = change > 0 ? "+" : "";
    parts.push(`${sign}${formatMoney(change, currency)}`);
  }
  if (changePercent != null) {
    const sign = changePercent > 0 ? "+" : "";
    parts.push(`${sign}${formatNumber(changePercent, 2)}%`);
  }
  return parts.join(" · ");
}

function formatBidAsk(
  bid: number | null | undefined,
  ask: number | null | undefined,
  currency: string | null | undefined,
): string {
  if (bid == null && ask == null) {
    return "—";
  }
  return `${formatMoney(bid, currency)} / ${formatMoney(ask, currency)}`;
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

function formatRatioOrPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  if (Math.abs(value) <= 1) {
    return formatPercent(value);
  }
  return `${formatNumber(value, 2)}%`;
}

function formatMoney(value: number | null | undefined, currency: string | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  const amount = value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return currency ? `${amount} ${currency}` : amount;
}

function formatCompact(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return value.toLocaleString(undefined, { notation: "compact", maximumFractionDigits: 2 });
}

function formatCompactMoney(value: number | null | undefined, currency: string | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  const amount = value.toLocaleString(undefined, { notation: "compact", maximumFractionDigits: 2 });
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
