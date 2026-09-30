"use client";

import { CardHeader, Skeleton } from "@heroui/react";

type PaymentHeaderProps = {
  loading: boolean;
  planName?: string;
  minutes: number;
  seconds: number;
  id: string;
};

export default function PaymentHeader({ loading, planName, minutes, seconds, id }: PaymentHeaderProps) {
  return (
    <CardHeader className="flex items-center justify-between">
      <div className="flex flex-col">
        <h1 className="text-2xl font-semibold">Pagamento PIX</h1>
        {loading ? (
          <Skeleton className="h-4 w-40 rounded-md" />
        ) : planName ? (
          <p className="text-foreground/70 text-sm">{planName} - #{id}</p>
        ) : (
          <p className="text-foreground/70 text-sm">Erro ao carregar</p>
        )}
      </div>
      <div className="text-right">
        <p className="text-sm text-foreground/70">Tempo restante</p>
        <p className="font-mono">
          {minutes.toString().padStart(2, "0")}:{seconds.toString().padStart(2, "0")}
        </p>
      </div>
    </CardHeader>
  );
}


