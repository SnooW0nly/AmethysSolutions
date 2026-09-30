import { Button } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { useMemo } from "react";


export function PaymentApprovedReceipt({
    planName,
    months,
    originalPrice,
    discountPercent,
    finalPrice,
    paymentId,
    createdAt,
    applicationId,
  }: {
    planName: string;
    months?: number | null;
    originalPrice: number;
    discountPercent?: number | null;
    finalPrice: number;
    paymentId: string;
    createdAt?: string;
    applicationId?: string;
  }) {
    const dateText = useMemo(() => {
      try {
        // Prefer backend-provided createdAt
        if (createdAt) return new Date(createdAt).toLocaleString("pt-BR");
        // Fallback: derive timestamp from Mongo ObjectId (first 8 hex chars are seconds)
        if (paymentId && /^[a-f\d]{24}$/i.test(paymentId)) {
          const secondsHex = paymentId.substring(0, 8);
          const seconds = parseInt(secondsHex, 16);
          if (!Number.isNaN(seconds)) {
            return new Date(seconds * 1000).toLocaleString("pt-BR");
          }
        }
        return "—";
      } catch {
        return "—";
      }
    }, [createdAt, paymentId]);
  
    return (
      <div className="w-full">
        <div className="flex items-center justify-between w-full">
          <div className="flex flex-col">
            <h3 className="text-xl font-semibold">Recibo do pagamento</h3>
            <p className="text-xs text-foreground/60">#{paymentId} • {dateText}</p>
          </div>
        </div>
        <hr className="border-foreground/10 my-3" />
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-foreground/70">Plano</span>
            <span className="font-medium">{planName}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-foreground/70">Duração</span>
            <span className="font-medium">{months ?? 0} {(months ?? 0) > 1 ? "meses" : "mês"}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-foreground/70">Data</span>
            <span className="font-medium">{dateText}</span>
          </div>
          <hr className="border-foreground/10 my-1" />
          <div className="flex items-center justify-between text-sm">
            <span className="text-foreground/70">Valor original</span>
            <span className="font-medium">{new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(originalPrice || 0))}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-foreground/70">Desconto</span>
            <span className={`font-medium ${Number(discountPercent || 0) > 0 ? 'text-success' : 'text-foreground'}`}>-{Number(discountPercent || 0)}%</span>
          </div>
          <hr className="border-foreground/10 my-1" />
          <div className="flex items-center justify-between text-sm">
            <span className="text-foreground/70">Total pago</span>
            <span className="text-lg font-semibold">{new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(finalPrice || 0))}</span>
          </div>
          <div className="">
            <Button
              color="primary"
              fullWidth
              className="w-full rounded-lg"
              onPress={() => {
                const target = applicationId ? `/dashboard/app/${applicationId}/overview` : "/dashboard";
                window.location.assign(target);
              }}
            >
              Ir para o painel <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="text-[10px]" />
            </Button>
          </div>
        </div>
      </div>
    );
  }