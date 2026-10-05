import { api } from "./client";

export type Profile = { profile_id: string; name: string; kind: "default" | "user" };

export type HouseType = {
  use_case: string;
  label: string;
  guideline_text: string;
  guideline_source: "default" | "yours";
  pdf: { doc_id: string; doc_title: string; filename: string; origin: string };
  pdf_source: "default" | "yours";
};

export function listProfiles() {
  return api<{ profiles: Profile[] }>("/api/v1/profiles");
}

export function createProfile(name: string) {
  return api<{ profile: Profile }>("/api/v1/profiles", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function deleteProfile(profileId: string) {
  return api<{ deleted: string }>(`/api/v1/profiles/${encodeURIComponent(profileId)}`, { method: "DELETE" });
}

export function listTypes(profileId: string) {
  return api<{ types: HouseType[]; disclaimer: string }>(
    `/api/v1/profiles/${encodeURIComponent(profileId)}/types`,
  );
}

export function saveGuideline(profileId: string, useCase: string, guideline_text: string) {
  return api<{ use_case: string; guideline_text: string; guideline_source: string }>(
    `/api/v1/profiles/${encodeURIComponent(profileId)}/guidelines/${encodeURIComponent(useCase)}`,
    { method: "PUT", body: JSON.stringify({ guideline_text }) },
  );
}

export function clearGuideline(profileId: string, useCase: string) {
  return api<{ use_case: string; guideline_text: string; guideline_source: string }>(
    `/api/v1/profiles/${encodeURIComponent(profileId)}/guidelines/${encodeURIComponent(useCase)}`,
    { method: "DELETE" },
  );
}
