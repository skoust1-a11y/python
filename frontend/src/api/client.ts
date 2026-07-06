import type {
  ApiError,
  DocumentDetailResponse,
  DocumentListResponse,
  DocumentUploadResponse,
  FeedbackRequest,
  FeedbackResponse,
  HealthResponse,
  QueryRequest,
  QueryResponse,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as ApiError;
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function listDocuments(skip = 0, limit = 50): Promise<DocumentListResponse> {
  return request<DocumentListResponse>(`/documents?skip=${skip}&limit=${limit}`);
}

export function getDocument(id: string): Promise<DocumentDetailResponse> {
  return request<DocumentDetailResponse>(`/document/${id}`);
}

export function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<DocumentUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      try {
        const body = JSON.parse(xhr.responseText) as DocumentUploadResponse | ApiError;
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body as DocumentUploadResponse);
        } else {
          reject(new Error((body as ApiError).detail || "Upload failed"));
        }
      } catch {
        reject(new Error("Invalid server response"));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
    xhr.open("POST", `${API_BASE}/upload`);
    xhr.send(form);
  });
}

export function queryDocuments(body: QueryRequest): Promise<QueryResponse> {
  return request<QueryResponse>("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function submitFeedback(body: FeedbackRequest): Promise<FeedbackResponse> {
  return request<FeedbackResponse>("/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
