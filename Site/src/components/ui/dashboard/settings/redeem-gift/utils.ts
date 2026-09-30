import { ExistingApp, GiftValidationResponse, RedeemSuccessData } from "./types";

export function isValidDate(date: Date): boolean {
  return !Number.isNaN(date.getTime());
}

export function formatDateSafe(input?: string | null): string {
  if (!input) return "-";
  const d = new Date(input);
  return isValidDate(d)
    ? d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" })
    : "-";
}

export function normalizeGiftValidation(payload: unknown): GiftValidationResponse {
  const base: GiftValidationResponse = {
    valid: false,
    message: "Não foi possível validar o gift.",
    data: undefined,
  };
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    const valid = typeof obj.valid === "boolean" ? obj.valid : false;
    const message =
      typeof obj.message === "string" ? obj.message : base.message;
    let data: GiftValidationResponse["data"];
    if (obj.data && typeof obj.data === "object") {
      const d = obj.data as Record<string, unknown>;
      data = {
        planName: String(d.planName ?? ""),
        months: Number(d.months ?? 0),
        days: Number(d.days ?? 0),
        expiresAt: d.expiresAt != null ? String(d.expiresAt) : undefined,
      };
    }
    return { valid, message, data };
  }
  return base;
}

export function normalizeAppsResponse(payload: unknown): ExistingApp[] {
  if (!payload || typeof payload !== "object") return [];
  const hasApps = (payload as any).applications;
  const list = Array.isArray(hasApps) ? (hasApps as unknown[]) : [];
  return list
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const it = item as Record<string, unknown>;
      const id = String(it._id ?? "");
      const name = String(it.name ?? "");
      const expiresAt = it.expiresAt != null ? String(it.expiresAt) : undefined;
      if (!id || !name) return null;
      return { _id: id, name, expiresAt } as ExistingApp;
    })
    .filter(Boolean) as ExistingApp[];
}

export function buildDurationLabel(months: number, days: number): string {
  const parts: string[] = [];
  if (months) parts.push(`${months} mês(es)`);
  if (days) parts.push(`${days} dia(s)`);
  return parts.join(" e ") || "—";
}

export function buildRedeemSuccessText(
  actionText: string,
  data?: RedeemSuccessData
): string {
  if (!data) {
    return `Gift ${actionText}!`;
  }
  const duration = buildDurationLabel(data.months, data.days);
  return `Gift ${actionText}! Você ganhou ${duration} de ${data.planName}!`;
}


