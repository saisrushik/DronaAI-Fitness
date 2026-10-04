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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    ...options,
    // The session lives in an httpOnly cookie, so it must be sent with every request.
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
  });

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
