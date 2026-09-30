"use client";

import { ReactNode } from "react";
import { Input, Select, SelectItem } from "@heroui/react";

type PaymentsFiltersProps = {
  planId: string;
  coupon: string;
  user: string;
  limit: number;
  onChange: (next: Partial<{ planId: string; coupon: string; user: string; limit: number }>) => void;
  actions?: ReactNode;
};

export function PaymentsFilters({ planId, coupon, user, limit, onChange, actions }: PaymentsFiltersProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
      <Input size="sm" label="Plano (id)" value={planId} onChange={(e) => onChange({ planId: e.target.value })} />
      <Input size="sm" label="Cupom" value={coupon} onChange={(e) => onChange({ coupon: e.target.value.toUpperCase() })} />
      <Input size="sm" label="Usuário (nome/email)" value={user} onChange={(e) => onChange({ user: e.target.value })} />
      <Select
        size="sm"
        className="min-w-[180px]"
        label="Itens por página"
        selectedKeys={new Set([String(limit)])}
        onSelectionChange={(keys) => {
          const value = Number(Array.from(keys as any)[0] || 20);
          onChange({ limit: value });
        }}
      >
        {[10, 20, 50, 100].map((n) => (
          <SelectItem key={String(n)}>{n}</SelectItem>
        ))}
      </Select>
      {actions ? actions : null}
    </div>
  );
}


