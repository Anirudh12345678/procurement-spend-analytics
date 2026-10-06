const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code = "API_ERROR",
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const requestInit = {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  };
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, requestInit);
  } catch (reason) {
    const method = (init?.method ?? "GET").toUpperCase();
    if (method !== "GET" || !(reason instanceof TypeError)) throw reason;
    await new Promise((resolve) => setTimeout(resolve, 150));
    response = await fetch(`${API_BASE}${path}`, requestInit);
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let code = "API_ERROR";
    try {
      const payload = (await response.json()) as {
        error?: { message?: string; code?: string };
      };
      message = payload.error?.message ?? message;
      code = payload.error?.code ?? code;
    } catch {
      // Keep the status-based error if the server did not return JSON.
    }
    throw new ApiError(message, response.status, code);
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
};

export function queryString(values: Record<string, string | number | undefined | null>): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  });
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}
