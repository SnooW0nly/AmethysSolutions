export async function fetchAdminPayments(params: { page: number; limit: number; planId?: string; coupon?: string; user?: string }) {
  const qs = new URLSearchParams({ page: String(params.page), limit: String(params.limit) });
  if (params.planId) qs.set("planId", params.planId);
  if (params.coupon) qs.set("coupon", params.coupon);
  if (params.user) qs.set("user", params.user);
  const res = await fetch(`/api/admin/payments?${qs.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Erro ao carregar pagamentos");
  return res.json();
}

export async function fetchAdminPaymentsStats(period: string) {
  const res = await fetch(`/api/admin/payments/stats?period=${period}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Erro ao carregar estatísticas");
  return res.json();
}


