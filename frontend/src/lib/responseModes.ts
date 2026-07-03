export type ResponseMode = "strict" | "explain" | "analysis";

export const RESPONSE_MODES: ResponseMode[] = [
  "strict",
  "explain",
  "analysis",
];

export const DEFAULT_RESPONSE_MODE: ResponseMode = "explain";

/** User-facing pill labels (maps to internal modes). */
export const RESPONSE_MODE_LABELS: Record<ResponseMode, string> = {
  strict: "📄 Evidence",
  explain: "💡 Explain",
  analysis: "⚖️ Analysis",
};

export const RESPONSE_MODE_DESCRIPTIONS: Record<ResponseMode, string> = {
  strict: "Documents only — always cite sources, never use outside knowledge",
  explain: "Documents first, with general legal knowledge when needed",
  analysis: "Structured legal review with risks, ambiguities, and recommendations",
};

const LEGACY_MODE_MAP: Record<string, ResponseMode> = {
  assisted: "explain",
  detailed: "explain",
  research: "analysis",
};

export function normalizeResponseMode(value: string | null | undefined): ResponseMode {
  if (value && RESPONSE_MODES.includes(value as ResponseMode)) {
    return value as ResponseMode;
  }
  if (value && value in LEGACY_MODE_MAP) {
    return LEGACY_MODE_MAP[value];
  }
  return DEFAULT_RESPONSE_MODE;
}

export function loadStoredResponseMode(): ResponseMode {
  try {
    return normalizeResponseMode(localStorage.getItem("responseMode"));
  } catch {
    return DEFAULT_RESPONSE_MODE;
  }
}

export function storeResponseMode(mode: ResponseMode): void {
  try {
    localStorage.setItem("responseMode", mode);
  } catch {
    // ignore storage errors
  }
}
