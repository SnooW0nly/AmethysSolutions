"use client";

import { useEffect, useState } from "react";
import { fetchAdminUserById } from "../services/adminUsers";
import type { AdminUser } from "../types";

type Options = {
  enabled?: boolean;
  initialUser?: Partial<AdminUser> | null;
};

export function useAdminUser(userId: string, options: Options = {}) {
  const { enabled = true, initialUser = null } = options;
  const [user, setUser] = useState<Partial<AdminUser> | null>(initialUser);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!enabled) return;
      setLoading(true);
      try {
        const data = await fetchAdminUserById(userId);
        if (!cancelled) setUser(data);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [userId, enabled]);

  return { user, loading };
}


