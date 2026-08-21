export interface HealthResponse {
  status: string;
  name: string;
  environment: string;
  providers: {
    llm: string;
    market_data: string;
    fundamental_data: string;
    news: string;
  };
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    detail?: string;
    issues?: Record<string, unknown>[];
  };
}
