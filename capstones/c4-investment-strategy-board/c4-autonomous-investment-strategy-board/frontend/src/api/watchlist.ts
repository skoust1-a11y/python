import { deleteJson, getJson, postJson } from "./client";
import type {
  WatchlistItem,
  WatchlistOpenResponse,
  WatchlistRemoval,
} from "@/models";

export function listWatchlist(): Promise<WatchlistItem[]> {
  return getJson<WatchlistItem[]>("/watchlist");
}

export function addWatchlistStock(symbol: string): Promise<WatchlistItem> {
  return postJson<WatchlistItem>("/watchlist", { symbol });
}

export function getWatchlistStock(symbol: string): Promise<WatchlistItem> {
  return getJson<WatchlistItem>(`/watchlist/${encodeURIComponent(symbol)}`);
}

export function removeWatchlistStock(symbol: string): Promise<WatchlistRemoval> {
  return deleteJson<WatchlistRemoval>(`/watchlist/${encodeURIComponent(symbol)}`);
}

export function openWatchlistStock(symbol: string): Promise<WatchlistOpenResponse> {
  return postJson<WatchlistOpenResponse>(
    `/watchlist/${encodeURIComponent(symbol)}/open`,
  );
}
