"use client";

import { AlertTriangle, Clock, RefreshCw, Ban } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@heroui/react";

interface ExpirationAlertProps {
  app: {
    _id: string;
    name: string;
    expiresAt: string;
    isBlocked?: boolean;
  };
}

export default function ExpirationAlert({ app }: ExpirationAlertProps) {
  const router = useRouter();

  // Calcula dias restantes
  const now = new Date();
  const expiresAt = new Date(app.expiresAt);
  const daysLeft = Math.ceil((expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  const isExpired = daysLeft <= 0;
  const isExpiringSoon = daysLeft > 0 && daysLeft <= 7;

  // Se está bloqueado
  if (app.isBlocked) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-red-500/20 rounded-xl">
            <Ban className="w-6 h-6 text-red-500" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-bold text-red-500 mb-2">
              Aplicação Bloqueada
            </h3>
            <p className="text-sm text-foreground/60 mb-4">
              Sua aplicação foi bloqueada por falta de pagamento. Renove agora para reativar.
            </p>
            <button
              onClick={() => router.push(`/dashboard/invoices?renew=${app._id}`)}
              className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-primary/30 flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Renovar Agora
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Se expirou
  if (isExpired) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-red-500/20 rounded-xl">
            <AlertTriangle className="w-6 h-6 text-red-500" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-bold text-red-500 mb-2">
              Aplicação Expirada
            </h3>
            <p className="text-sm text-foreground/60 mb-4">
              Sua aplicação expirou em {expiresAt.toLocaleDateString("pt-BR")}. 
              Renove agora para evitar o bloqueio permanente.
            </p>
            <button
              onClick={() => router.push(`/dashboard/invoices?renew=${app._id}`)}
              className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-primary/30 flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Renovar Agora
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Se está perto de vencer (7 dias ou menos)
  if (isExpiringSoon) {
    return (
      <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex flex-col">
            <h3 className="text-lg font-semibold text-yellow-500 mb-2">
              Vencimento próximo
            </h3>
            <p className="text-sm text-foreground/60">
              Sua aplicação <strong>{app.name}</strong> vence em{" "}
              <strong className="text-yellow-500">
                {daysLeft} {daysLeft === 1 ? "dia" : "dias"}
              </strong>{" "}
              ({expiresAt.toLocaleDateString("pt-BR")}). 
              Renove agora para evitar bloqueio.
            </p>
          </div>
          <Button
            onPress={() => router.push(`/dashboard/invoices?renew=${app._id}`)}
            color="primary"
            startContent={<RefreshCw className="w-4 h-4" />}
            className="font-normal text-sm rounded-lg w-fit"
          >
            Renovar
          </Button>
        </div>
      </div>
    );
  }

  // Não mostra nada se tiver mais de 7 dias
  return null;
}
