import { useCallback, useEffect, useState } from "react";
import { ExistingApp } from "../types";
import { normalizeAppsResponse } from "../utils";

/**
 * Hook para carregar e expor as aplicações existentes do usuário
 */
export function useExistingApps() {
  const [existingApps, setExistingApps] = useState<ExistingApp[]>([]);

  const reloadApps = useCallback(async (): Promise<void> => {
    try {
      const response = await fetch("/api/apps", {
        credentials: "include",
      });
      if (!response.ok) {
        // não quebra o fluxo; UI continua funcional
        return;
      }
      const json = (await response.json().catch(() => null)) as unknown;
      const apps = normalizeAppsResponse(json);
      setExistingApps(apps);
    } catch {
      // falhas transitórias ignoradas
    }
  }, []);

  useEffect(() => {
    void reloadApps();
  }, [reloadApps]);

  return { existingApps, reloadApps };
}


