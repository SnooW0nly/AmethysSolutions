"use client";

import React from "react";

export type PaymentMethod = "pix" | "paypal" | "card";

export function PaymentMethodSelector({
  value,
  onChange,
}: {
  value: PaymentMethod;
  onChange: (method: PaymentMethod) => void;
}) {
  const methods: { id: PaymentMethod; label: string; description: string; enabled: boolean }[] = [
    { id: "pix", label: "PIX", description: "Pagamento aprovado na hora, sem renovação automática", enabled: true },
    { id: "paypal", label: "PayPal", description: "Pagamento via PayPal, taxas inclusas, renovação automática", enabled: false },
    { id: "card", label: "Cartão (Crédito/Débito)", description: "Pagamento via cartão de crédito ou débito, renovação automática", enabled: false },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
      {methods.map((m) => {
        const isSelected = value === m.id;
        return (
          <button
            key={m.id}
            type="button"
            disabled={!m.enabled}
            onClick={() => m.enabled && onChange(m.id)}
            className={
              `text-left rounded-md border w-full p-3 transition-colors select-none ` +
              (m.enabled
                ? isSelected
                  ? "border-primary bg-primary/10"
                  : "border-foreground/10 bg-foreground/2 hover:bg-foreground/5"
                : "border-foreground/10 bg-foreground/2 opacity-50 cursor-not-allowed")
            }
          >
            <div className="flex flex-col gap-1">
              <p className="text-foreground/90 text-sm font-bold">{m.label}</p>
              <p className="text-foreground/70 text-[12px]">{m.description}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}


