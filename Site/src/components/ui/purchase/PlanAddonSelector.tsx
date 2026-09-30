"use client";

import { useEffect, useState } from "react";
import { Switch, Chip } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPuzzlePiece } from "@fortawesome/free-solid-svg-icons";

export type AddonOption = {
  id: string;
  name: string;
  shortDescription: string;
  extraValue: number;
};

type Props = {
  planId: string;
  selectedAddons: string[];
  onToggle: (addonId: string, extraValue: number, selected: boolean) => void;
};

export function PlanAddonSelector({ planId, selectedAddons, onToggle }: Props) {
  const [addons, setAddons] = useState<AddonOption[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!planId) return;
    setLoading(true);
    fetch(`/api/info/addons?planId=${encodeURIComponent(planId)}`)
      .then((r) => r.json())
      .then((data) => {
        setAddons(Array.isArray(data?.addons) ? data.addons : []);
      })
      .catch(() => setAddons([]))
      .finally(() => setLoading(false));
  }, [planId]);

  if (loading || addons.length === 0) return null;

  return (
    <div className="mt-2">
      <div className="flex items-center gap-1.5 mb-1">
        <FontAwesomeIcon icon={faPuzzlePiece} className="text-foreground/50 text-xs" />
        <p className="text-foreground/70 text-sm">Adicionais</p>
      </div>
      <div className="flex flex-col gap-2">
        {addons.map((addon) => {
          const isSelected = selectedAddons.includes(addon.id);
          return (
            <div
              key={addon.id}
              className={`rounded-lg border p-3 transition-colors ${
                isSelected
                  ? "border-primary/40 bg-primary/5"
                  : "border-foreground/10 bg-foreground/2"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold">{addon.name}</span>
                    <Chip
                      size="sm"
                      color="primary"
                      variant="flat"
                      className="text-[10px] font-bold"
                    >
                      +R$ {addon.extraValue.toFixed(2)}
                    </Chip>
                  </div>
                  {addon.shortDescription && (
                    <p className="text-xs text-foreground/50 mt-0.5">{addon.shortDescription}</p>
                  )}
                </div>
                <Switch
                  size="sm"
                  isSelected={isSelected}
                  onValueChange={(v) => onToggle(addon.id, addon.extraValue, v)}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}