"use client";

import { useEffect, useState } from "react";
import { Gift, Loader2 } from "lucide-react";
import { GiftInput } from "./redeem-gift/components/GiftInput";
import { ValidationAlert } from "./redeem-gift/components/ValidationAlert";
import { MessageAlert } from "./redeem-gift/components/MessageAlert";
import { AppSelection } from "./redeem-gift/components/AppSelection";
import { useGiftValidation } from "./redeem-gift/hooks/useGiftValidation";
import { useExistingApps } from "./redeem-gift/hooks/useExistingApps";
import { useRedeemGift } from "./redeem-gift/hooks/useRedeemGift";

export default function RedeemGiftSection() {
  const { giftCode, setGiftCode, validationResult, validating } = useGiftValidation();
  const { existingApps, reloadApps } = useExistingApps();
  const { redeemGift, loading, message, clearMessage } = useRedeemGift();
  const [showAppSelection, setShowAppSelection] = useState<boolean>(false);

  // Reload de apps quando o código é validado com sucesso
  useEffect(() => {
    if (validationResult?.valid) {
      void reloadApps();
    }
  }, [validationResult?.valid, reloadApps]);

  function handleCodeChange(value: string) {
    setGiftCode(value.toUpperCase());
    clearMessage();
  }

  async function handleRedeem(appId: string | null) {
    const success = await redeemGift({ code: giftCode, appId });
    if (success) {
      setGiftCode("");
      setShowAppSelection(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 mt-2 md:w-[50%]">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="text-foreground/70 text-sm font-medium">Resgatar Gift</span>
        </div>

        <div className="bg-foreground/5 rounded-lg p-4">
          <div className="flex flex-col gap-3">
            {/* Input do código */}
            <GiftInput
              value={giftCode}
              onChange={handleCodeChange}
              disabled={loading}
              validating={validating}
            />

            {/* Resultado da validação */}
            {validationResult && !validating && (
              <ValidationAlert result={validationResult} />
            )}

            {/* Mensagem de sucesso/erro */}
            {message && <MessageAlert message={message} />}

            {/* Seleção de bot */}
            {showAppSelection && (
              <AppSelection
                apps={existingApps}
                monthsToAdd={validationResult?.data?.months}
                daysToAdd={validationResult?.data?.days}
                loading={loading}
                onRedeem={handleRedeem}
                onCancel={() => setShowAppSelection(false)}
              />
            )}

            {/* Botão de resgatar */}
            {!showAppSelection && (
              <button
                onClick={() => setShowAppSelection(true)}
                disabled={validationResult?.valid !== true}
                className="w-full px-4 py-2.5 cursor-pointer bg-primary hover:bg-primary/90 disabled:bg-foreground/10 disabled:text-foreground/30 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Resgatando...
                  </>
                ) : (
                  <>
                    <Gift className="w-4 h-4" />
                    Resgatar Gift
                  </>
                )}
              </button>
            )}

            <p className="text-xs text-foreground/50 text-center">
              Digite o código do gift para validar e resgatar seu presente
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
