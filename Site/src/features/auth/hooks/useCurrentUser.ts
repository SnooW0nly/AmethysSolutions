// Hook: useCurrentUser
// Provides the authenticated user, loading state, error, and a refresh() action.
import { useEffect, useState, useCallback } from "react";
import type { User } from "@/config/dashboard";
import { getCurrentSession, logout as apiLogout } from "@/lib/api/session";

export function useCurrentUser() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const data = await getCurrentSession();
      setUser(data?.user ?? null);
    } catch (e: any) {
      setError(e?.message || "Erro ao buscar sessão");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    await apiLogout().catch(() => {});
    setUser(null);
  }, []);

  return { user, loading, error, refresh, logout } as const;
}


