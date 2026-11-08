import type { ApiErrorBody } from "./health";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail?: string;
  readonly issues?: Record<string, unknown>[];

  constructor(
    message: string,
    options: {
      status: number;
      code: string;
      detail?: string;
      issues?: Record<string, unknown>[];
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.detail = options.detail;
    this.issues = options.issues;
  }

  static fromResponse(status: number, body: unknown, fallback: string): ApiError {
    const parsed = parseErrorBody(body);
    return new ApiError(parsed?.error.message || fallback, {
      status,
      code: parsed?.error.code ?? "http_error",
      detail: parsed?.error.detail,
      issues: parsed?.error.issues,
    });
  }
}

function parseErrorBody(body: unknown): ApiErrorBody | null {
  if (!body || typeof body !== "object" || !("error" in body)) {
    return null;
  }
  const error = (body as ApiErrorBody).error;
  if (!error || typeof error.message !== "string") {
    return null;
  }
  return body as ApiErrorBody;
}

export function toErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred.";
}
