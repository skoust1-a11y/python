import type { ApiError } from "@/models/errors";

export type AsyncStatus = "idle" | "loading" | "success" | "empty" | "error";

export interface AsyncState<T> {
  status: AsyncStatus;
  data: T | null;
  error: ApiError | Error | null;
}

export function idleState<T>(): AsyncState<T> {
  return { status: "idle", data: null, error: null };
}

export function loadingState<T>(data: T | null = null): AsyncState<T> {
  return { status: "loading", data, error: null };
}

export function successState<T>(data: T, isEmpty = false): AsyncState<T> {
  return { status: isEmpty ? "empty" : "success", data, error: null };
}

export function errorState<T>(error: ApiError | Error): AsyncState<T> {
  return { status: "error", data: null, error };
}
