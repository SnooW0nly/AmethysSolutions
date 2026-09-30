"use client";

import { Button, Skeleton } from "@heroui/react";
import { useRouter } from "next/navigation";

export function PaymentLoadingSkeleton() {
  return (
    <>
      <div className="rounded-md">
        <Skeleton className="h-56 w-56 rounded-md" />
      </div>
      <div className="flex flex-col items-center gap-2 w-full">
        <Skeleton className="h-10 w-60 rounded-md" />
        <Skeleton className="h-3 w-full max-w-xl rounded-md" />
      </div>
    </>
  );
}

export function PaymentLoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="text-danger text-center">
      <p className="font-medium">{message}</p>
      <Button color="primary" onPress={onRetry}>Tentar novamente</Button>
    </div>
  );
}

export function PaymentCancelled({ planId }: { planId?: string }) {
  const router = useRouter();
  return (
    <div className="w-full flex items-center justify-center">
      <div className="text-danger text-center flex flex-col items-center gap-3 bg-foreground/5 border border-danger/20 rounded-xl p-6 max-w-md w-full">
        <p className="font-medium text-danger">Pagamento cancelado</p>
        <p className="text-foreground/70 text-sm">Seu pagamento foi cancelado. Você pode tentar novamente escolhendo o plano desejado.</p>
        <Button color="primary" onPress={() => router.push(`/purchase?plan=${planId ?? ""}`)}>Criar novo pagamento</Button>
      </div>
    </div>
  );
}

