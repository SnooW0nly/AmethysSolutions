// Centralized Apps API layer
// All HTTP requests related to applications should go through here.
// Types are imported from existing project types to avoid duplication.
import type { AppInfo } from "@/types/app";

type Json = Record<string, any>;

async function handleJson<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as unknown as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error: any = new Error(data?.error || `Request failed (${res.status})`);
    if (data?.errorCode) error.code = data.errorCode;
    error.status = res.status;
    error.data = data;
    throw error;
  }
  return data as T;
}

export async function getApps(): Promise<{ applications: any[] }> {
  const res = await fetch("/api/apps", { cache: "no-store", credentials: "include", headers: { accept: "application/json" } });
  return handleJson(res);
}

export async function getAppInfo(id: string): Promise<{ application: AppInfo }> {
  const res = await fetch(`/api/apps/${id}/info`, { cache: "no-store", credentials: "include", headers: { accept: "application/json" } });
  return handleJson(res);
}

export async function startApp(id: string): Promise<Json> {
  const res = await fetch(`/api/apps/${id}/start`, { method: "POST", credentials: "include", headers: { accept: "application/json" } });
  return handleJson(res);
}

export async function stopApp(id: string): Promise<Json> {
  const res = await fetch(`/api/apps/${id}/stop`, { method: "POST", credentials: "include", headers: { accept: "application/json" } });
  return handleJson(res);
}

export async function restartApp(id: string): Promise<Json> {
  const res = await fetch(`/api/apps/${id}/restart`, { method: "POST", credentials: "include", headers: { accept: "application/json" } });
  return handleJson(res);
}

export async function getExpiringApps(): Promise<{ applications: any[] }> {
  const res = await fetch("/api/apps/expiring", { cache: "no-store", credentials: "include", headers: { accept: "application/json" } });
  const data = await handleJson<any>(res);
  // Normalize various backend shapes to a stable interface
  if (Array.isArray(data)) {
    return { applications: data };
  }
  if (data?.applications && Array.isArray(data.applications)) {
    return { applications: data.applications };
  }
  if (data?.data && Array.isArray(data.data)) {
    return { applications: data.data };
  }
  return { applications: [] };
}


