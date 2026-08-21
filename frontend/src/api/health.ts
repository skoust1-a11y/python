import { getJson } from "./client";
import type { HealthResponse } from "@/models";

export function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}
