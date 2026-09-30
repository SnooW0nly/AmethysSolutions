"use client";

import { useEffect, useState } from "react";
import { notFound } from "next/navigation";
import type { AppInfo } from "@/types/app";
import { getAppInfo } from "@/lib/api/apps";

export function useAppInfo(id?: string) {
  const [app, setApp] = useState<AppInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  async function refetch(options?: { silent?: boolean }) {
    if (!id) return;
    const silent = options?.silent ?? true;
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await getAppInfo(id);
      if (!data?.application) {
        notFound();
      }
      setApp(data.application as AppInfo);
    } catch (e: any) {
      setError(e?.message || "Erro");
    } finally {
      if (!silent) setLoading(false);
    }
  }

  useEffect(() => {
    let aborted = false;
    if (!id) return;
    (async () => {
      try {
        await refetch({ silent: false });
      } finally {
        if (!aborted) {
          // refetch already manages loading state
        }
      }
    })();
    return () => {
      aborted = true;
    };
  }, [id]);

  return { app, loading, error, refetch } as const;
}


