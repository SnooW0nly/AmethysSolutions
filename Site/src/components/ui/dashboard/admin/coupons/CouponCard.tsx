"use client";

import { Button } from "@heroui/react";
import type { Coupon } from "@/types/coupons";

export function CouponCard({ coupon, onEdit, onToggleArchive }: { coupon: Coupon; onEdit: (c: Coupon) => void; onToggleArchive: (c: Coupon) => void }) {
  return (
    <div className={`rounded-lg border ${coupon.archived ? "border-foreground/20 opacity-70" : "border-foreground/10"} bg-foreground/2 p-4 flex flex-col gap-2`}>
      <div className="flex justify-between">
        <div>
          <h3 className="text-lg font-semibold">{coupon.name}</h3>
          <p className="text-foreground/70 text-sm gap-2">
            {Number(coupon.percent)}% de desconto
          </p>
          {coupon.maxUses ? <p className="text-foreground/70 text-sm">{coupon.usedCount || 0}/{coupon.maxUses} usos</p> : <p className="text-foreground/70 text-sm">{coupon.usedCount || 0} usos</p>}
        </div>
        <div className="flex flex-col items-end">
          <Button size="sm" variant="light" onPress={() => onEdit(coupon)}>Editar</Button>
          <Button size="sm" variant="light" onPress={() => onToggleArchive(coupon)}>{coupon.archived ? "Restaurar" : "Arquivar"}</Button>
        </div>
      </div>
    </div>
  );
}


