import { api } from "./client";
import type { User } from "./types";

export function signup(email: string, password: string, full_name?: string) {
  return api<{ user_id: string; email: string; role: string }>("/api/v1/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name }),
  });
}

export function login(email: string, password: string) {
  return api<{ access_token: string; expires_in: number; user: User }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function me() {
  return api<User>("/api/v1/auth/me");
}
