"use client";

import React from "react";

export type PlanVariant = {
  id: string;
  name: string;
  value: number;
  description: string;
  discount?: number;
  months: number;
};

export function DurationSelector({
  variants,
  selectedId,
  onSelect,
}: {
  variants: PlanVariant[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-3 gap-2">
      {variants.map((variant) => {
        const isSelected = variant.id === selectedId;
        return (
          <button
            key={variant.id}
            type="button"
            onClick={() => onSelect(variant.id)}
            className={
              `text-left rounded-md border w-full p-3 transition-colors select-none cursor-pointer ` +
              (isSelected
                ? "border-primary bg-primary/10"
                : "border-foreground/10 bg-foreground/2 hover:bg-foreground/5")
            }
          >
            <div className="flex items-baseline justify-between gap-1">
              <p className="text-foreground/90 text-sm font-bold">{variant.name}</p>
              {variant.discount ? (
                <span className="text-success text-[12px] bg-success/10 px-2 rounded-full">-{variant.discount}%</span>
              ) : null}
            </div>
            <div className="flex items-end gap-1">
              <span className="text-foreground/80 text-sm font-semibold">R$ {variant.value}</span>
              <span className="text-foreground/70 text-xs">/ {variant.description}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}


