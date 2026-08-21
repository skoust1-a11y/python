import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { LineChart, Loader2, RefreshCw, Search, Star, Trash2 } from "lucide-react";
import { Button, Card, PageHeader, PageStatus } from "@/components";
import { searchStocks, selectStock } from "@/api/stocks";
import {
  addWatchlistStock,
  listWatchlist,
  openWatchlistStock,
  removeWatchlistStock,
} from "@/api/watchlist";
import { errorState, idleState, loadingState, successState, type AsyncState } from "@/lib/asyncState";
import { ApiError, toErrorMessage } from "@/models/errors";
import type { InstrumentMatch, WatchlistItem } from "@/models";

const SEARCH_DEBOUNCE_MS = 300;
const SYMBOL_PATTERN = /^\^?[A-Za-z0-9][A-Za-z0-9.\-]{0,31}$/;

/** Independent screen. Monitoring and navigation only; analysis stays on Stock Analyzer. */
export function WatchlistPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<AsyncState<WatchlistItem[]>>(loadingState());
  const [reloadNonce, setReloadNonce] = useState(0);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [search, setSearch] = useState<AsyncState<InstrumentMatch[]>>(idleState());
  const [searchHint, setSearchHint] = useState<string | null>(null);
  const [busySymbol, setBusySymbol] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [actionError, setActionError] = useState<unknown>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const searchRequest = useRef(0);
  const listRequest = useRef(0);

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
    void searchStocks(debouncedQuery)
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
  }, [debouncedQuery]);

  useEffect(() => {
    const requestId = ++listRequest.current;
    let cancelled = false;
    setItems((current) => loadingState(current.data));
    void listWatchlist()
      .then((watched) => {
        if (cancelled || listRequest.current !== requestId) {
          return;
        }
        setItems(successState(watched, watched.length === 0));
      })
      .catch((error) => {
        if (!cancelled && listRequest.current === requestId) {
          setItems(errorState(asError(error)));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [reloadNonce]);

  const watched = items.data ?? [];
  const watchedSymbols = new Set(watched.map((item) => item.symbol));
  const listBusy = items.status === "loading" && !items.data;
  const refreshing = items.status === "loading";
  const formBusy = adding || analyzing || refreshing;

  async function addSymbol(token: string) {
    const candidate = token.trim();
    if (!candidate || formBusy) {
      return;
    }
    setAdding(true);
    setActionError(null);
    setActionMessage(null);
    try {
      const added = await addWatchlistStock(candidate);
      setItems((current) => {
        const existing = current.data ?? [];
        return successState(
          [added, ...existing.filter((item) => item.symbol !== added.symbol)],
        );
      });
      setActionMessage(`${added.symbol} is now on Watchlist. Open Stock Analyzer when you want a full analysis.`);
      setQuery("");
      setDebouncedQuery("");
      setSearch(idleState());
      setSearchHint(null);
    } catch (error) {
      if (error instanceof ApiError && error.code === "conflict") {
        setActionMessage(`${candidate.toUpperCase()} is already on Watchlist.`);
        return;
      }
      setActionError(error);
    } finally {
      setAdding(false);
    }
  }

  async function analyzeSymbol(token: string) {
    const candidate = token.trim();
    if (!candidate || formBusy) {
      return;
    }
    setAnalyzing(true);
    setActionError(null);
    setActionMessage(null);
    try {
      const selected = await selectStock(candidate);
      navigate(stockPath(selected.symbol));
    } catch (error) {
      if (looksLikeSymbol(candidate)) {
        navigate(stockPath(candidate.toUpperCase()));
        return;
      }
      setActionError(error);
    } finally {
      setAnalyzing(false);
    }
  }

  function resolveSearchToken(): string | null {
    const token = query.trim();
    if (!token) {
      return null;
    }
    const matches = search.data ?? [];
    const exact = matches.find((item) => item.symbol.toUpperCase() === token.toUpperCase());
    if (exact) {
      return exact.symbol;
    }
    if (matches.length === 1) {
      return matches[0].symbol;
    }
    if (looksLikeSymbol(token)) {
      return token;
    }
    if (matches.length > 1) {
      setSearchHint("Select an instrument below to add it or open Stock Analyzer.");
      return null;
    }
    setSearchHint("No instrument matched that search. Try a ticker symbol or a listed company name.");
    return null;
  }

  function onAddSubmit(event: FormEvent) {
    event.preventDefault();
    setSearchHint(null);
    const token = resolveSearchToken();
    if (token) {
      void addSymbol(token);
    }
  }

  function onAnalyzeClick() {
    setSearchHint(null);
    const token = resolveSearchToken();
    if (token) {
      void analyzeSymbol(token);
    }
  }

  async function openAnalyzer(item: WatchlistItem) {
    if (busySymbol) {
      return;
    }
    setBusySymbol(item.symbol);
    setActionError(null);
    try {
      const opened = await openWatchlistStock(item.symbol);
      navigate(stockPath(opened.symbol));
    } catch {
      navigate(stockPath(item.symbol));
    } finally {
      setBusySymbol(null);
    }
  }

  async function removeSymbol(item: WatchlistItem) {
    if (busySymbol) {
      return;
    }
    setBusySymbol(item.symbol);
    setActionError(null);
    setActionMessage(null);
    try {
      await removeWatchlistStock(item.symbol);
      setItems((current) => {
        const remaining = (current.data ?? []).filter((row) => row.symbol !== item.symbol);
        return successState(remaining, remaining.length === 0);
      });
      setActionMessage(`${item.symbol} was removed from Watchlist.`);
    } catch (error) {
      setActionError(error);
    } finally {
      setBusySymbol(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Watchlist"
        description="Monitor selected symbols and open them in Stock Analyzer. This view does not run AI analysis."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => setReloadNonce((value) => value + 1)}
              disabled={refreshing || adding || analyzing || Boolean(busySymbol)}
            >
              {items.status === "loading" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Refresh
            </Button>
            <Button variant="secondary" onClick={() => navigate("/stocks")}>
              <LineChart className="h-4 w-4" />
              Open Stock Analyzer
            </Button>
          </div>
        }
      />

      <div className="space-y-4">
        <AddCard
          query={query}
          search={search}
          searchHint={searchHint}
          adding={adding}
          analyzing={analyzing}
          disabled={formBusy}
          watchedSymbols={watchedSymbols}
          actionMessage={actionMessage}
          actionError={actionError}
          onQueryChange={(value) => {
            setQuery(value);
            setSearchHint(null);
            setActionError(null);
          }}
          onSubmit={onAddSubmit}
          onAnalyze={onAnalyzeClick}
          onAddMatch={(match) => void addSymbol(match.symbol)}
          onAnalyzeMatch={(match) => void analyzeSymbol(match.symbol)}
        />

        <PageStatus
          loading={listBusy}
          loadingLabel="Loading watched symbols..."
          error={items.status === "error" && !items.data ? items.error : undefined}
          errorTitle="Watchlist could not be loaded"
          onRetry={() => setReloadNonce((value) => value + 1)}
          empty={items.status === "empty"}
          emptyTitle="Watchlist is empty"
          emptyDescription="Add a ticker above to monitor current price and day change. Open Stock Analyzer when you want a full analysis of a name."
          emptyAction={
            <Button variant="secondary" onClick={() => navigate("/stocks")}>
              <LineChart className="h-4 w-4" />
              Analyze a stock
            </Button>
          }
        >
          {watched.length ? (
            <WatchedTable
              items={watched}
              busySymbol={busySymbol}
              refreshing={refreshing}
              disabled={Boolean(busySymbol) || formBusy}
              onOpen={(item) => void openAnalyzer(item)}
              onRemove={(item) => void removeSymbol(item)}
            />
          ) : null}
        </PageStatus>
      </div>
    </>
  );
}

function AddCard({
  query,
  search,
  searchHint,
  adding,
  analyzing,
  disabled,
  watchedSymbols,
  actionMessage,
  actionError,
  onQueryChange,
  onSubmit,
  onAnalyze,
  onAddMatch,
  onAnalyzeMatch,
}: {
  query: string;
  search: AsyncState<InstrumentMatch[]>;
  searchHint: string | null;
  adding: boolean;
  analyzing: boolean;
  disabled: boolean;
  watchedSymbols: Set<string>;
  actionMessage: string | null;
  actionError: unknown;
  onQueryChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  onAnalyze: () => void;
  onAddMatch: (match: InstrumentMatch) => void;
  onAnalyzeMatch: (match: InstrumentMatch) => void;
}) {
  const matches = search.data ?? [];
  const busy = disabled;
  return (
    <Card title="Add or analyze a stock">
      <p className="text-sm text-slate-600">
        Adding a symbol keeps monitoring here. Analysis always opens in Stock Analyzer.
      </p>
      <form className="mt-3 flex flex-col gap-3 lg:flex-row" onSubmit={onSubmit}>
        <label className="block flex-1 text-sm">
          <span className="font-medium text-slate-700">Ticker or company name</span>
          <input
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-600"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search AAPL, Microsoft, or another listed name"
            maxLength={64}
            autoComplete="off"
            disabled={busy}
          />
        </label>
        <div className="flex flex-wrap items-end gap-2">
          <Button type="submit" disabled={!query.trim() || busy}>
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Star className="h-4 w-4" />}
            {adding ? "Adding..." : "Add to Watchlist"}
          </Button>
          <Button variant="secondary" onClick={onAnalyze} disabled={!query.trim() || busy}>
            {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <LineChart className="h-4 w-4" />}
            {analyzing ? "Opening..." : "Analyze"}
          </Button>
        </div>
      </form>
      {search.status === "error" ? (
        <p className="mt-3 text-sm text-amber-800">
          {toErrorMessage(search.error)}. You can still add or analyze a ticker if you already know the symbol.
        </p>
      ) : null}
      {search.status === "empty" ? (
        <p className="mt-3 text-sm text-slate-500">No instruments matched “{query.trim()}”.</p>
      ) : null}
      {searchHint ? <p className="mt-3 text-sm text-slate-600">{searchHint}</p> : null}
      {actionMessage ? <p className="mt-3 text-sm text-emerald-800">{actionMessage}</p> : null}
      {actionError ? <p className="mt-3 text-sm text-red-700">{toErrorMessage(actionError)}</p> : null}
      {matches.length ? (
        <ul className="mt-3 divide-y divide-slate-100 rounded-md border border-slate-200">
          {matches.map((match) => {
            const watching = watchedSymbols.has(match.symbol);
            return (
              <li
                key={`${match.symbol}-${match.exchange ?? ""}`}
                className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 text-sm"
              >
                <span>
                  <span className="font-medium text-slate-900">{match.symbol}</span>
                  <span className="mt-0.5 block text-xs text-slate-500">
                    {match.name ?? "Unnamed instrument"}
                    {match.exchange ? ` · ${match.exchange}` : ""}
                    {match.currency ? ` · ${match.currency}` : ""}
                  </span>
                </span>
                <span className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => onAddMatch(match)}
                    disabled={busy || watching}
                  >
                    {watching ? "On watchlist" : "Add"}
                  </Button>
                  <Button variant="secondary" onClick={() => onAnalyzeMatch(match)} disabled={busy}>
                    Analyze
                  </Button>
                </span>
              </li>
            );
          })}
        </ul>
      ) : search.status === "loading" && query.trim() ? (
        <p className="mt-3 flex items-center gap-2 text-sm text-slate-500">
          <Search className="h-4 w-4" />
          Searching...
        </p>
      ) : null}
    </Card>
  );
}

function WatchedTable({
  items,
  busySymbol,
  refreshing,
  disabled,
  onOpen,
  onRemove,
}: {
  items: WatchlistItem[];
  busySymbol: string | null;
  refreshing: boolean;
  disabled: boolean;
  onOpen: (item: WatchlistItem) => void;
  onRemove: (item: WatchlistItem) => void;
}) {
  return (
    <Card
      title="Watched stocks"
      action={
        refreshing ? (
          <span className="flex items-center gap-1 text-xs text-slate-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Updating quotes...
          </span>
        ) : (
          <span className="text-xs font-normal text-slate-500">
            {items.length} {items.length === 1 ? "symbol" : "symbols"}
          </span>
        )
      }
    >
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-2 py-2 font-medium">Symbol</th>
              <th className="px-2 py-2 font-medium">Price</th>
              <th className="px-2 py-2 font-medium">Day change</th>
              <th className="px-2 py-2 font-medium">% change</th>
              <th className="px-2 py-2 font-medium">Last updated</th>
              <th className="px-2 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const quote = item.quote;
              const currency = item.currency ?? quote?.currency;
              const busy = busySymbol === item.symbol;
              return (
                <tr key={item.symbol} className="border-b border-slate-100 align-top">
                  <td className="px-2 py-3">
                    <p className="font-medium text-slate-900">{item.symbol}</p>
                    <p className="text-xs text-slate-500">
                      {item.name ?? "Unnamed instrument"}
                      {item.exchange ? ` · ${item.exchange}` : ""}
                    </p>
                    {item.unavailable.length ? (
                      <p className="mt-1 text-xs text-amber-800">
                        Unavailable: {item.unavailable.map(humanizeField).join(", ")}. Not invented.
                      </p>
                    ) : null}
                  </td>
                  <td className="px-2 py-3 tabular-nums font-medium text-slate-800">
                    {formatMoney(quote?.value ?? null, currency)}
                  </td>
                  <td className={`px-2 py-3 tabular-nums ${signedClass(quote?.change)}`}>
                    {formatSigned(quote?.change, currency)}
                  </td>
                  <td className={`px-2 py-3 tabular-nums ${signedClass(quote?.change_percent)}`}>
                    {formatPercentChange(quote?.change_percent)}
                  </td>
                  <td className="px-2 py-3 text-slate-600">
                    {formatDate(quote?.timestamp)}
                    {quote?.source ? (
                      <span className="mt-0.5 block text-xs text-slate-400">
                        {quote.source.provider} · {quote.source.source}
                      </span>
                    ) : null}
                  </td>
                  <td className="px-2 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Button variant="secondary" onClick={() => onOpen(item)} disabled={disabled}>
                        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <LineChart className="h-4 w-4" />}
                        Open Analyzer
                      </Button>
                      <Button variant="ghost" onClick={() => onRemove(item)} disabled={disabled}>
                        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                        Remove
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-slate-500">
        Quotes come from the configured market adapter. Missing prices stay blank. Last updated is the quote
        timestamp from that source. AI analysis is not run from this screen.
      </p>
    </Card>
  );
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

function formatSigned(value: number | null | undefined, currency: string | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatMoney(value, currency)}`;
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
