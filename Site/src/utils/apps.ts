export function calculateRemainingProgressPercent(
  expiresAt?: string,
  months?: number
): number {
  if (!expiresAt || !months || months <= 0) return 0;
  const expiryDate = new Date(expiresAt);
  const startDate = new Date(expiryDate);
  // Estimate the plan start date by subtracting its duration in months
  startDate.setMonth(startDate.getMonth() - months);

  const totalMs = expiryDate.getTime() - startDate.getTime();
  if (totalMs <= 0) return 0;

  const now = Date.now();
  const remainingMs = Math.max(0, expiryDate.getTime() - now);
  const percent = (remainingMs / totalMs) * 100;
  return Math.max(0, Math.min(100, Math.round(percent)));
}

export function calculateRemainingAndTotalDays(
  expiresAt?: string,
  months?: number
): { remainingDays: number; totalDays: number } {
  if (!expiresAt) return { remainingDays: 0, totalDays: 0 };

  const expiryDate = new Date(expiresAt);
  const nowDate = new Date();
  // Normalize to midnight to avoid partial-day off-by-one oscillations
  const normalizeMidnight = (d: Date) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const expiryMs = normalizeMidnight(expiryDate);
  const nowMs = normalizeMidnight(nowDate);

  const remainingMs = Math.max(0, expiryMs - nowMs);
  const dayMs = 24 * 60 * 60 * 1000;
  const remainingDays = Math.ceil(remainingMs / dayMs);

  // If we know the plan duration in months and we're inside the current cycle,
  // estimate total days using (expiry - (expiry - months)).
  // If not inside the current cycle yet (expiry further than months ahead),
  // fall back to totalDays = remainingDays to avoid misleading "clamping".
  if (months && months > 0) {
    const estimatedCycleStart = new Date(expiryMs);
    estimatedCycleStart.setMonth(estimatedCycleStart.getMonth() - months);
    const startMs = normalizeMidnight(estimatedCycleStart);

    if (nowMs >= startMs) {
      const totalMs = Math.max(0, expiryMs - startMs);
      const totalDays = Math.max(1, Math.ceil(totalMs / dayMs));
      return { remainingDays, totalDays };
    }
  }

  // Default: total equals remaining (shows like "61/61 dias")
  return { remainingDays, totalDays: remainingDays };
}

export function getHostingStatusDisplay(
  status?: string | null
): { label: string; dotClass: string; bgColor: string; animated?: boolean } {
  const normalized = (status || "").toString().trim().toLowerCase();
  if (!normalized) return { label: "Não encontrado", dotClass: "bg-gray-400", bgColor: "gray-400" };

  if (["running", "online", "on", "active"].includes(normalized)) {
    return { label: "Online", dotClass: "bg-green-500/80", bgColor: "green-500" };
  }

  if (["restarting", "reiniciando"].includes(normalized)) {
    return { label: "Reiniciando", dotClass: "bg-yellow-500/80", bgColor: "yellow-500", animated: true };
  }

  if (
    [
      "stopped",
      "offline",
      "off",
      "shutdown",
      "stopping",
      "erro",
      "error",
    ].includes(normalized)
  ) {
    return { label: "Offline", dotClass: "bg-red-500/80", bgColor: "red-500" };
  }

  return { label: "Não encontrado", dotClass: "bg-gray-400", bgColor: "gray-400" };
}


