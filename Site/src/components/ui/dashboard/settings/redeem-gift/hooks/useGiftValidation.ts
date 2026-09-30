import { useEffect, useState } from "react";
import { GiftValidationResponse } from "../types";
import { normalizeGiftValidation } from "../utils";

/**
 * Hook responsável por:
 * - State do código
 * - Debounce de validação (~500ms)
 * - Chamada à API de validação com tratamento de erro
 */
export function useGiftValidation() {
  const [giftCode, setGiftCode] = useState<string>("");
  const [validating, setValidating] = useState<boolean>(false);
  const [validationResult, setValidationResult] =
    useState<GiftValidationResponse | null>(null);

  useEffect(() => {
    const trimmed = giftCode.trim();
    if (!trimmed) {
      setValidationResult(null);
      return;
    }
    setValidating(true);
    const timeoutId = setTimeout(() => {
      void validateGift(trimmed);
    }, 500);
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [giftCode]);

  async function validateGift(code: string): Promise<void> {
    try {
      const response = await fetch("/api/gifts/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ code: code.toUpperCase() }),
      });
      if (!response.ok) {
        setValidationResult({
          valid: false,
          message: "Não foi possível validar o gift. Tente novamente.",
        });
        return;
      }
      const json = (await response.json().catch(() => null)) as unknown;
      const normalized = normalizeGiftValidation(json);
      setValidationResult(normalized);
    } catch {
      setValidationResult({
        valid: false,
        message: "Erro de rede ao validar o gift.",
      });
    } finally {
      setValidating(false);
    }
  }

  return {
    giftCode,
    setGiftCode,
    validating,
    validationResult,
  };
}


