"use client";

import { useAffiliateTracking } from "@/hooks/useAffiliateTracking";

/**
 * Componente invisível que captura ?ref=CODIGO da URL
 * e salva no localStorage para uso no checkout.
 * Também registra o clique no backend.
 */
export function AffiliateTracker() {
  useAffiliateTracking();
  return null;
}