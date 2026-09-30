// Centralized Session/Auth API
import type { User } from "@/config/dashboard";

type SessionResponse = { user: User | null };

async function handleJson<T>(res: Response): Promise<T> {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error: any = new Error(data?.error || `Request failed (${res.status})`);
    error.status = res.status;
    error.data = data;
    throw error;
  }
  return data as T;
}

export async function getCurrentSession(): Promise<SessionResponse> {
  const res = await fetch(`/api/auth/session`, {
    cache: "no-store",
    credentials: "include",
    headers: { accept: "application/json" },
  });
  if (res.status === 204) return { user: null };
  return handleJson(res);
}

export async function logout(): Promise<void> {
  const res = await fetch(`/api/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: { accept: "application/json" },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const error: any = new Error(data?.error || `Logout failed (${res.status})`);
    error.status = res.status;
    error.data = data;
    throw error;
  }
}


