"use client";

import React from "react";
import { DurationSelector, type PlanVariant } from "@/components/ui/purchase/DurationSelector";

export function DurationBlock({ variants, selectedId, onSelect }: { variants: PlanVariant[]; selectedId: string; onSelect: (id: string) => void }) {
  return (
    <div className="mt-2">
      <p className="text-foreground/70 text-sm">Duração do plano</p>
      <div className="bg-foreground/2 p-2 rounded-lg border border-foreground/10 w-full mt-1">
        {variants?.length ? (
          <DurationSelector variants={variants} selectedId={selectedId} onSelect={onSelect} />
        ) : (
          <div className="text-sm text-foreground/60 p-2">Sem opções de duração disponíveis.</div>
        )}
      </div>
    </div>
  );
}


