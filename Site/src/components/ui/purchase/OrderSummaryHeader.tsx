"use client";

import React from "react";

export function OrderSummaryHeader({
  originalValue,
  finalPrice,
  description,
  hasDiscount,
  couponPercent,
  paymentMethod,
}: {
  originalValue: number;
  finalPrice: number;
  description: string;
  hasDiscount: boolean;
  couponPercent?: number | null;
  paymentMethod: string;
}) {
  return (
    <div className="flex flex-col">
      <p className="text-foreground/90 text-lg font-bold">Resumo do pedido</p>
      <p className="text-foreground/70 text-sm">Verifique as informações do plano e o método de pagamento escolhido para finalizar a compra. Quando estiver pronto, você será redirecionado para a página de pagamento.</p>
      <hr className="my-2 border-foreground/10" />
      <div className="flex flex-col gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm text-foreground/70">Valor final {couponPercent ? <span className="text-success text-[12px]">(Cupom -{couponPercent}%)</span> : ''}</p>
          <div className="flex items-end gap-1">
            {couponPercent ? (
              <>
                <span className="text-foreground/70 line-through">R$ {originalValue}</span>
                <span className="text-2xl font-semibold text-success">R$ {finalPrice}</span>
              </>
            ) : (
              <span className="text-2xl font-semibold">R$ {originalValue}</span>
            )}
            <span className="text-[12px] text-foreground/70 self-end mb-1">/ {description}</span>
          </div>
          <div className="mt-2">
            <p className="text-sm text-foreground/70">Método de pagamento</p>
            <div className="flex gap-1">
              <span className="text-2xl font-semibold">{paymentMethod.toUpperCase()}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


