// Date/time formatting helpers for UI
// Keep functions small and deterministic

export function formatBrazilianDate(d?: string | Date | null): string {
  if (!d) return "";
  const date = typeof d === "string" ? new Date(d) : d;
  return date.toLocaleDateString("pt-BR");
}

export function formatRemainingDays(remainingDays: number): string {
  if (remainingDays <= 0) return "Expira hoje";
  if (remainingDays === 1) return "1 dia restante";
  return `${remainingDays} dias restantes`;
}

export function formatSince(d?: string | number | Date | null): string {
  if (!d) return "";
  const date =
    typeof d === "string" || typeof d === "number" ? new Date(d) : d;
  const now = Date.now();
  const started = date instanceof Date ? date.getTime() : NaN;
  if (Number.isNaN(started)) return "";
  let diffMs = now - started;
  if (diffMs < 0) diffMs = 0;

  const minuteMs = 60 * 1000;
  const hourMs = 60 * minuteMs;
  const dayMs = 24 * hourMs;

  const days = Math.floor(diffMs / dayMs);
  diffMs %= dayMs;
  const hours = Math.floor(diffMs / hourMs);
  diffMs %= hourMs;
  const minutes = Math.floor(diffMs / minuteMs);

  const parts: string[] = [];
  if (days > 0) {
    parts.push(days === 1 ? "1 dia" : `${days} dias`);
    if (hours > 0) {
      parts.push(hours === 1 ? "1 hora" : `${hours} horas`);
    }
  } else if (hours > 0) {
    parts.push(hours === 1 ? "1 hora" : `${hours} horas`);
    if (minutes > 0) {
      parts.push(minutes === 1 ? "1 minuto" : `${minutes} minutos`);
    }
  } else {
    if (minutes > 0) {
      parts.push(minutes === 1 ? "1 minuto" : `${minutes} minutos`);
    } else {
      parts.push("menos de 1 minuto");
    }
  }

  return parts.join(" e ");
}

