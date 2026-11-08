import { getJson } from "./client";
import type { DashboardOverview } from "@/models";

export function getDashboard(): Promise<DashboardOverview> {
  return getJson<DashboardOverview>("/dashboard");
}
