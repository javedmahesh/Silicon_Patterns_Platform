/**
 * Thin fetch wrapper around the FastAPI backend.
 * - Base path from VITE_API_BASE_URL (default "/api"; dev proxy strips it to root).
 * - Sends X-API-Key when VITE_API_KEY is set (backend only enforces if SP_API_KEY is set).
 * - Normalizes errors into ApiError so the UI can render the backend's `detail`.
 */
import { AUTH_BYPASS, authStore } from "@/lib/auth/store";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/+$/, "");
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Structured auth/lifecycle detail — {code, message} — used by the account-governance
 * endpoints (see backend/services.py::_lifecycle_error) so the UI can show the actual
 * reason ("account_pending", "account_disabled", ...) instead of a generic
 * "Request failed (403)". `code` is stable; `message` is the human-readable fallback. */
export interface ApiErrorDetail {
  code: string;
  message: string;
}

export function apiErrorDetail(e: unknown): ApiErrorDetail | null {
  if (!(e instanceof ApiError)) return null;
  const d = e.detail;
  if (d && typeof d === "object" && "code" in d && "message" in d) return d as ApiErrorDetail;
  return null;
}

/** Best-effort human-readable message for any error caught from `request()`. */
export function apiErrorMessage(e: unknown): string {
  const structured = apiErrorDetail(e);
  if (structured) return structured.message;
  return e instanceof ApiError ? e.message : "Action not allowed";
}

export type QueryParams = Record<string, string | number | boolean | null | undefined>;

function buildQuery(params?: QueryParams): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === null || v === undefined || v === "") continue;
    sp.append(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

interface RequestOptions {
  method?: string;
  params?: QueryParams;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", params, body, headers = {}, signal } = opts;
  const url = `${BASE}${path}${buildQuery(params)}`;

  const init: RequestInit = {
    method,
    signal,
    headers: { Accept: "application/json", ...headers },
  };
  if (API_KEY) (init.headers as Record<string, string>)["X-API-Key"] = API_KEY;
  const token = authStore.token();
  if (token) (init.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  // Dev bypass: tell the backend which synthetic role to act as (ignored in prod).
  if (AUTH_BYPASS) (init.headers as Record<string, string>)["X-Dev-Role"] = authStore.devRole();
  if (body !== undefined) {
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    throw new ApiError(
      0,
      `Could not reach the API at ${url}. Is the backend running (python -m backend.main)?`,
      err,
    );
  }

  const text = await res.text();
  const data = text ? safeJson(text) : null;

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? (data as { detail: unknown }).detail
        : text;
    const message = typeof detail === "string" && detail ? detail : `Request failed (${res.status})`;
    // Session expired / revoked → drop it and bounce to login. Not for the login
    // exchange itself, whose 401/403 should surface on the login page.
    if (res.status === 401 && !path.startsWith("/auth/")) {
      authStore.clear();
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    }
    throw new ApiError(res.status, message, detail);
  }

  return data as T;
}
