import { useState } from "react";
import { useRouter } from "next/navigation";
import { GiftMessage, RedeemResponse } from "../types";
import { buildRedeemSuccessText } from "../utils";

/**
 * Hook para orquestrar o fluxo de resgate:
 * - Chamada ao backend
 * - Mensagens de sucesso/erro
 * - Redirecionamento pós-sucesso (2s)
 */
export function useRedeemGift() {
  const router = useRouter();
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<GiftMessage | null>(null);

  function clearMessage() {
    setMessage(null);
  }

  async function redeemGift(params: {
    code: string;
    appId: string | null;
  }): Promise<boolean> {
    const { code, appId } = params;
    if (!code.trim()) {
      setMessage({ type: "error", text: "Digite um código de gift" });
      return false;
    }

    setLoading(true);
    setMessage(null);
    try {
      const body: { code: string; applicationId?: string } = {
        code: code.trim().toUpperCase(),
      };
      if (appId) {
        body.applicationId = appId;
      }
      const response = await fetch("/api/gifts/redeem", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        let friendly = "Erro ao resgatar gift";
        try {
          const errJson = (await response.json()) as { message?: string };
          if (errJson?.message) friendly = errJson.message;
        } catch {
          // ignore
        }
        setMessage({ type: "error", text: friendly });
        return false;
      }
      const data = (await response.json().catch(() => null)) as RedeemResponse | null;
      const success = Boolean(data?.success);
      if (success) {
        const actionText = appId ? "adicionados ao seu bot" : "resgatado com sucesso";
        const text = buildRedeemSuccessText(actionText, data?.data);
        setMessage({ type: "success", text });
        setTimeout(() => {
          router.push("/dashboard");
        }, 2000);
        return true;
      }
      setMessage({
        type: "error",
        text: data?.message || "Erro ao resgatar gift",
      });
      return false;
    } catch {
      setMessage({ type: "error", text: "Erro ao resgatar gift" });
      return false;
    } finally {
      setLoading(false);
    }
  }

  return { redeemGift, loading, message, clearMessage };
}


