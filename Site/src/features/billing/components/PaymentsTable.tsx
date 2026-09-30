"use client";

import type { AdminPayment } from "../types";

export function PaymentsTable({ items, loading }: { items: AdminPayment[]; loading: boolean }) {
  return (
    <div className="rounded-lg border border-foreground/10 bg-foreground/2 p-3">
      {loading ? (
        <div className="text-sm text-foreground/60">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="text-sm text-foreground/60">Sem pagamentos aprovados</div>
      ) : (
        <div className="w-full overflow-x-auto">
          <div className="min-w-[980px] flex flex-col gap-2 max-h-96 overflow-auto">
            <div className="text-[11px] text-foreground/60 grid grid-cols-7 gap-2 px-1">
              <span>ID</span>
              <span>Plano</span>
              <span>Valor</span>
              <span>Cupom</span>
              <span>Data</span>
              <span>Status</span>
              <span>Usuário</span>
            </div>
            <div className="h-[1px] bg-foreground/10" />
            {items.map((p) => {
              const userIdDisplay = String(p.user?._id || p.userId || "");
              return (
                <div key={String(p._id || p.id)} className="text-xs text-foreground/80 grid grid-cols-7 gap-2 items-center">
                  <span className="font-mono break-all" title={String(p._id || p.id)}>{String(p._id || p.id)}</span>
                  <span>{p.plan?.name}</span>
                  <span>{new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(p.priceFinal || 0))}</span>
                  <span>{p.coupon?.code || "-"} ({Number(p.coupon?.discountPercent || 0)}%)</span>
                  <span>{new Date(p.createdAt || (p._id ? new Date(parseInt(String(p._id).slice(0,8), 16) * 1000).toISOString() : Date.now())).toLocaleString("pt-BR")}</span>
                  <span className="text-success font-semibold">{p.status}</span>
                  <span className="truncate font-mono" title={userIdDisplay}>{userIdDisplay || "-"}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}


