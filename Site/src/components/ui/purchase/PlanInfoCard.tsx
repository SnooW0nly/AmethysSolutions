"use client";

import React from "react";
import type { PlanVariant } from "@/components/ui/purchase/DurationSelector";

type AppliedCoupon = { name: string; percent: number } | null;

export function PlanInfoCard({
  name,
  description,
  selectedVariant,
  coupon,
  finalPrice,
}: {
  name: string;
  description: string;
  selectedVariant: PlanVariant | null;
  coupon: AppliedCoupon;
  finalPrice: number;
}) {
  return (
    <div>
      <p className="text-foreground/70 text-sm">Informações do plano</p>
      <div className="flex flex-col lg:flex-row gap-2 bg-foreground/2 p-5 rounded-lg border border-foreground/10 w-full justify-between mt-1">
        <div className="w-1/1">
          <p className="text-foreground/90 text-sm font-bold">{name}</p>
          <p className="text-foreground/70 text-sm">{description}</p>
        </div>
      </div>
    </div>
  );
}


