const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** FastAPI returns a string for HTTPException and a list for validation errors. */
function readError(body: unknown): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => String((item as { msg?: string }).msg ?? "").replace(/^Value error, /, ""))
      .filter(Boolean)
      .join(" ");
  }
  return "Something went wrong. Please try again.";
}

/** Fired when the session can't be renewed, so the app can drop the signed-in user. */
export const SESSION_EXPIRED_EVENT = "auth:session-expired";

// Endpoints whose 401 means "bad credentials" rather than "access token expired".
const NO_REFRESH = new Set(["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"]);

let refreshing: Promise<boolean> | null = null;

/** Renews the access token. Concurrent callers share one request, since each refresh rotates the token. */
function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch(`${API_BASE}/api/v1/auth/refresh`, { method: "POST", credentials: "include" })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const send = () =>
    fetch(`${API_BASE}/api/v1${path}`, {
      ...options,
      // The session lives in httpOnly cookies, so they must be sent with every request.
      credentials: "include",
      headers: { "Content-Type": "application/json", ...options.headers },
    });

  let response = await send();
  if (response.status === 401 && !NO_REFRESH.has(path)) {
    if (await refreshSession()) {
      response = await send();
    } else {
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
  }

  if (response.status === 429) {
    throw new Error("Too many attempts. Please wait a minute and try again.");
  }
  if (!response.ok) {
    throw new Error(readError(await response.json().catch(() => null)));
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
