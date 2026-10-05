import { api } from "./client";
import type { ScreenDefinition, ScreenRun } from "./types";

export function screenFields() {
  return api<{ fields: Array<{ field: string; type: string; ops: string[] }> }>("/api/v1/screens/fields");
}

export function runScreen(definition: ScreenDefinition, profileId?: string) {
  const q = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : "";
  return api<ScreenRun>(`/api/v1/screens/run${q}`, {
    method: "POST",
    body: JSON.stringify({ definition }),
  });
}

export function screenFromNl(query: string, profileId?: string) {
  const q = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : "";
  return api<ScreenRun & { definition: ScreenDefinition }>(`/api/v1/screens/from-nl${q}`, {
    method: "POST",
    body: JSON.stringify({ query, auto_run: true }),
  });
}

export function listScreens(profileId?: string) {
  const q = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : "";
  return api<{
    screens: Array<{ screen_id: string; name: string; description?: string; definition: ScreenDefinition }>;
  }>(`/api/v1/screens${q}`);
}

export function saveScreen(name: string, definition: ScreenDefinition, profileId?: string) {
  const q = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : "";
  return api<{ screen_id: string; name: string }>(`/api/v1/screens${q}`, {
    method: "POST",
    body: JSON.stringify({ name, definition }),
  });
}
