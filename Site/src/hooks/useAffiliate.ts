"use client";

import { useEffect, useState, useCallback } from "react";

export interface AffiliateStats {
  code: string;
  link: string;
  clicks: number;
  conversions: number;
  rewardDays: number;
  claimedDays: number;
  pendingDays: number;
  rewardApps: Array<{
    applicationId: string;
    days: number;
    createdAt: string;
  }>;
  conversionHistory: Array<{
    paymentId: string;
    buyerUserId: string;
    createdAt: string;
    rewarded: boolean;
    rewardDays: number;
  }>;
  createdAt: string;
}

export function useAffiliate() {
  const [stats, setStats] = useState<AffiliateStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/affiliates/me", { credentials: "include" });
      if (!res.ok) throw new Error("Falha ao carregar dados");
      const json = await res.json();
      if (json.success) setStats(json.data);
      else throw new Error(json.message || "Erro desconhecido");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { stats, loading, error, reload: load };
}