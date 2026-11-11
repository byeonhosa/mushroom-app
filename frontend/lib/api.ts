// The API is always reached on the page's own origin, under /api.
//
// In production the Caddy proxy sends /api/* to the API container. In
// development and in the browser tests, next.config.js rewrites /api/* to the
// API named by API_PROXY_TARGET. Either way the browser sees one origin, so
// the session cookie travels with every request and no CORS is involved.
export const API_BASE = "/api";

/** An API refusal, carrying the HTTP status and the server's own sentence. */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Turn an error response into one plain sentence for the operator. */
async function describeFailure(res: Response): Promise<string> {
  const fallback =
    res.status >= 500
      ? "The server had a problem. Try again in a moment."
      : `The request was refused (${res.status}).`;
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    return fallback;
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  // FastAPI validation errors: a list of {loc, msg}.
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item: { loc?: unknown[]; msg?: string }) => {
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : undefined;
        const message = String(item.msg ?? "is not valid").replace(/^Value error, /, "");
        return typeof field === "string" && field !== "body" ? `${field.replace(/_/g, " ")}: ${message}` : message;
      })
      .join(" ");
  }
  return fallback;
}

/** Called when the API says the session is missing or over. Set by the app shell. */
let onSignedOut: (() => void) | null = null;

export function setSignedOutHandler(handler: (() => void) | null) {
  onSignedOut = handler;
}

async function request<T>(path: string, init: RequestInit, expectBody: boolean): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    credentials: "same-origin",
    ...init,
  });
  if (!res.ok) {
    // /auth/* reports its own 401s (a wrong password is not an expired session).
    if (res.status === 401 && !path.startsWith("/auth/") && onSignedOut) onSignedOut();
    throw new ApiError(res.status, await describeFailure(res));
  }
  if (!expectBody || res.status === 204) return undefined as T;
  return res.json();
}

function jsonInit(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, {}, true);
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, jsonInit("POST", body), true);
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, jsonInit("PATCH", body), true);
}

export function apiDelete(path: string): Promise<void> {
  return request<void>(path, { method: "DELETE" }, false);
}
