"use client";

import { Card, CardBody, CardHeader, Skeleton } from "@heroui/react";

type Props = {
  loading: boolean;
  planName?: string;
  months?: number | null;
  planPrice?: number;
  couponCode?: string | null;
  couponDiscount?: number | null;
  priceFinal?: number;
};

export default function PurchaseSummary({
  loading,
  planName,
  months,
  planPrice,
  couponCode,
  couponDiscount,
  priceFinal,
}: Props) {
  const safeMonths = months ?? 0;
  return (
    <aside className="w-full md:w-1/3">
      <Card className="border border-foreground/10 bg-foreground/2 rounded-xl p-3 h-full flex items-center justify-between flex-col">
        <CardHeader className="pb-0">
          <div className="flex flex-col">
            <h2 className="text-xl font-semibold">Resumo</h2>
            <p className="text-sm text-foreground/60">Veja as informações do seu pedido e finalize o pagamento seguindo as instruções.</p>
          </div>
        </CardHeader>
        <CardBody className="flex flex-col gap-3">
          {loading ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-24 rounded-md" />
                <Skeleton className="h-4 w-32 rounded-md" />
              </div>
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-24 rounded-md" />
                <Skeleton className="h-4 w-16 rounded-md" />
              </div>
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-28 rounded-md" />
                <Skeleton className="h-4 w-24 rounded-md" />
              </div>
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-20 rounded-md" />
                <Skeleton className="h-4 w-28 rounded-md" />
              </div>
              <hr className="border-foreground/10" />
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-24 rounded-md" />
                <Skeleton className="h-6 w-36 rounded-md" />
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Plano</span>
                  <div className="h-[1px] w-full bg-foreground/10" />
                </div>
                <div className="flex items-center gap-2 justify-between">
                  <span className="text-sm text-foreground/70">Nome</span>
                  <span className="text-sm font-medium">{planName}</span>
                </div>
                <div className="flex items-center gap-2 justify-between">
                  <span className="text-sm text-foreground/70">Duração</span>
                  <span className="text-sm font-medium">{safeMonths} {safeMonths > 1 ? "meses" : "mês"}</span>
                </div>
                <div className="flex items-center gap-2 justify-between">
                  <span className="text-sm text-foreground/70">Preço</span>
                  <span className="text-sm font-medium">{new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(planPrice || 0))}</span>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Cupom</span>
                  <div className="h-[1px] w-full bg-foreground/10" />
                </div>
                <div className="flex items-center gap-2 justify-between">
                  <span className="text-sm text-foreground/70">Nome</span>
                  <span className="text-sm font-medium">{couponCode || '—'}</span>
                </div>
                <div className="flex items-center gap-2 justify-between">
                  <span className="text-sm text-foreground/70">Desconto</span>
                  <span className={`text-sm font-medium ${Number(couponDiscount || 0) > 0 ? 'text-success' : 'text-foreground'}`}>- {Number(couponDiscount || 0)}%</span>
                </div>
              </div>
              <hr className="border-foreground/10" />
              <div className="flex items-center justify-between">
                <span className="text-sm text-foreground/70">Valor final</span>
                <span className="text-lg font-semibold">{new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(priceFinal || 0))}</span>
              </div>
            </div>
          )}
        </CardBody>
      </Card>
    </aside>
  );
}


