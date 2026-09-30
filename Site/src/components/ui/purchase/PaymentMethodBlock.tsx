"use client";

import React from "react";
import { PaymentMethodSelector, type PaymentMethod } from "@/components/ui/purchase/PaymentMethodSelector";

export function PaymentMethodBlock({ value, onChange }: { value: PaymentMethod; onChange: (m: PaymentMethod) => void }) {
  return (
    <div className="mt-2">
      <p className="text-foreground/70 text-sm">Método de pagamento</p>
      <div className="bg-foreground/2 p-2 rounded-lg border border-foreground/10 w-full mt-1">
        <PaymentMethodSelector value={value} onChange={onChange} />
      </div>
    </div>
  );
}


