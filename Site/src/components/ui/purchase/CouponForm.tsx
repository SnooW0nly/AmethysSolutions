"use client";

import React from "react";
import { Button, Input } from "@heroui/react";

export function CouponForm({
  value,
  error,
  isApplying,
  hasApplied,
  onChange,
  onApply,
}: {
  value: string;
  error: string | null;
  isApplying: boolean;
  hasApplied: boolean;
  onChange: (v: string) => void;
  onApply: () => void;
}) {
  return (
    <div>
      <div className="flex flex-col gap-1">
        <p className="text-foreground/70 text-sm">Cupom de desconto{hasApplied ? <span className="text-success text-[12px]"> • Cupom aplicado</span> : ''}</p>
        <div className="flex items-start gap-2">
          <Input
            className="flex-1"
            size="md"
            placeholder="Digite seu cupom"
            radius="sm"
            value={value.toUpperCase()}
            onValueChange={(v) => onChange(v)}
            isInvalid={!!error}
            errorMessage={error ?? undefined}
            isDisabled={hasApplied}
          />
          <Button
            size="md"
            color="primary"
            radius="sm"
            onPress={onApply}
            isLoading={isApplying}
            isDisabled={hasApplied || !value.trim()}
          >
            Aplicar
          </Button>
        </div>
      </div>
    </div>
  );
}


