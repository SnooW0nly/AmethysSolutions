"use client";

import { useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";

const STORAGE_KEY = "affiliate_ref";
const STORAGE_EXPIRY_KEY = "affiliate_ref_expiry";
const TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 dias

/**
 * Salva o código de afiliado no sessionStorage com TTL de 7 dias.
 * Chamado automaticamente quando há ?ref=CODE na URL.
 */
export function useAffiliateTracking() {
  const searchParams = useSearchParams();

  const registerClick = useCallback(async (code: string) => {
    try {
      await fetch("/api/affiliates/click", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
    } catch {
      // silencia erros de rede
    }
  }, []);

  useEffect(() => {
    const ref = searchParams.get("ref");
    if (!ref) return;

    // Salva no localStorage com expiração
    try {
      localStorage.setItem(STORAGE_KEY, ref.toUpperCase());
      localStorage.setItem(STORAGE_EXPIRY_KEY, String(Date.now() + TTL_MS));
    } catch {
      // localStorage pode estar bloqueado
    }

    // Registra o clique no backend
    registerClick(ref);
  }, [searchParams, registerClick]);
}

/**
 * Retorna o código de afiliado salvo (se ainda válido).
 */
export function getStoredAffiliateCode(): string | null {
  try {
    const code = localStorage.getItem(STORAGE_KEY);
    const expiry = Number(localStorage.getItem(STORAGE_EXPIRY_KEY) || "0");

    if (!code || Date.now() > expiry) {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(STORAGE_EXPIRY_KEY);
      return null;
    }

    return code;
  } catch {
    return null;
  }
}

/**
 * Limpa o código de afiliado após conversão.
 */
export function clearAffiliateCode() {
  try {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_EXPIRY_KEY);
  } catch {
    // ignore
  }
}