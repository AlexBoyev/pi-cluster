import { createContext, useCallback, useContext, useState } from "react";

interface AuthState {
  accessToken: string | null;
  username: string | null;
  role: string | null;
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccess: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function parseJwtPayload(token: string): Record<string, string> {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return {};
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() => ({
    accessToken: localStorage.getItem("access_token"),
    username: localStorage.getItem("username"),
    role: localStorage.getItem("role"),
  }));

  const login = useCallback(async (username: string, password: string) => {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error((data as { detail?: string }).detail ?? "Login failed");
    }
    const { access_token, refresh_token } = await res.json() as {
      access_token: string;
      refresh_token: string;
    };
    const payload = parseJwtPayload(access_token);
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    localStorage.setItem("username", payload.sub ?? username);
    localStorage.setItem("role", payload.role ?? "viewer");
    setState({ accessToken: access_token, username: payload.sub ?? username, role: payload.role ?? "viewer" });
  }, []);

  const logout = useCallback(() => {
    fetch("/api/v1/auth/logout", { method: "POST" }).catch(() => {});
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    setState({ accessToken: null, username: null, role: null });
  }, []);

  const refreshAccess = useCallback(async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return false;
    const res = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const { access_token } = await res.json() as { access_token: string };
    const payload = parseJwtPayload(access_token);
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("username", payload.sub ?? "");
    localStorage.setItem("role", payload.role ?? "viewer");
    setState((prev) => ({ ...prev, accessToken: access_token }));
    return true;
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refreshAccess }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
