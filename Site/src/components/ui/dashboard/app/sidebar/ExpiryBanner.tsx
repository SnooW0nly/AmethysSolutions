"use client";

import { Progress } from "@heroui/react";
import {
  calculateRemainingAndTotalDays,
  calculateRemainingProgressPercent,
} from "@/utils/apps";

type ExpiryBannerProps = {
  expiresAt?: string | null;
  months?: number | null;
};

export function ExpiryBanner({ expiresAt, months }: ExpiryBannerProps) {
  const hasExpiry = !!expiresAt && !!months && months > 0;
  if (!hasExpiry) return null;

  const { remainingDays, totalDays } = calculateRemainingAndTotalDays(
    expiresAt,
    months
  );
  const percent = calculateRemainingProgressPercent(
    expiresAt,
    months
  );

  const expiryLabel = new Date(expiresAt).toLocaleDateString("pt-BR");

  return (
    <div className="rounded-lg border border-foreground/10 p-2">
      <div className="flex items-center justify-between text-[11px] text-foreground/70">
        <span>Expira: {expiryLabel}</span>
        <span>
          {remainingDays} {remainingDays === 1 ? "dia restante" : "dias restantes"}
        </span>
      </div>
      <div className="mt-1">
        <Progress value={percent} size="sm" aria-label="Progresso de expiração" />
      </div>
    </div>
  );
}


