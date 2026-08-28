const BASE = "/api/v1";

async function tryRefresh(): Promise<string | null> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return null;
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) return null;
  const { access_token } = await res.json() as { access_token: string };
  localStorage.setItem("access_token", access_token);
  return access_token;
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  let token = localStorage.getItem("access_token");

  const makeHeaders = (t: string | null): HeadersInit => ({
    "Content-Type": "application/json",
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
    ...options?.headers,
  });

  let res = await fetch(`${BASE}${path}`, { ...options, headers: makeHeaders(token) });

  if (res.status === 401) {
    token = await tryRefresh();
    if (token) {
      res = await fetch(`${BASE}${path}`, { ...options, headers: makeHeaders(token) });
    } else {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.reload();
      throw new Error("Session expired");
    }
  }

  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}
