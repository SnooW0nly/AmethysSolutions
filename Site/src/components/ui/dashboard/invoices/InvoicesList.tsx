"use client";

import { useState, useEffect } from "react";
import { FileText, CheckCircle, Clock, XCircle, RefreshCw } from "lucide-react";
import { Button } from "@heroui/react";

interface Payment {
  _id: string;
  priceFinal: number;
  status: string;
  plan: {
    name: string;
    months: number;
  };
  createdAt: string;
  efiId: string;
}

export default function InvoicesList() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    loadPayments();
  }, [filter]);

  const loadPayments = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filter !== "all") {
        params.append("status", filter);
      }

      const response = await fetch(`/api/invoices/list?${params}`, {
        credentials: "include",
      });

      if (!response.ok) {
        console.error("Erro HTTP:", response.status, response.statusText);
        const text = await response.text();
        console.error("Resposta:", text);
        return;
      }

      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        console.error("Resposta não é JSON:", contentType);
        const text = await response.text();
        console.error("Conteúdo:", text?.substring(0, 200) || text);
        return;
      }

      const data = await response.json();
      
      if (data.success) {
        setPayments(data.data.payments || []);
      } else {
        console.error("API retornou erro:", data.message);
      }
    } catch (error) {
      console.error("Erro ao carregar faturas:", error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      approved: {
        icon: CheckCircle,
        text: "Aprovado",
        color: "text-green-500",
        bg: "bg-green-500/10",
        border: "border-green-500/30",
      },
      pending: {
        icon: Clock,
        text: "Pendente",
        color: "text-yellow-500",
        bg: "bg-yellow-500/10",
        border: "border-yellow-500/30",
      },
      expired: {
        icon: XCircle,
        text: "Expirado",
        color: "text-red-500",
        bg: "bg-red-500/10",
        border: "border-red-500/30",
      },
      completed: {
        icon: CheckCircle,
        text: "Completo",
        color: "text-green-500",
        bg: "bg-green-500/10",
        border: "border-green-500/30",
      },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 ${config.bg} ${config.color} border ${config.border} rounded text-xs`}>
        <Icon className="w-3 h-3" />
        {config.text}
      </span>
    );
  };

  if (loading) {
    return null; // Não mostra loading, deixa a página principal controlar
  }

  return (
    <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-3 p-6 border-b border-foreground/10">
        <div className="flex flex-col">
          <h2 className="text-lg font-semibold">Faturas</h2>
          <p className="text-sm text-foreground/70">Veja o estado das suas faturas</p>
        </div>
        <div className="flex flex-col gap-3 md:flex-row md:items-center justify-between">
          {/* Filtros */}
          <div className="flex gap-2">
            <Button
              onPress={() => setFilter("all")}
              className={`px-4 py-2 rounded-lg text-sm transition-all font-normal  ${
                filter === "all"
                  ? "bg-primary text-white shadow-lg shadow-primary/30"
                  : "bg-background/50 hover:bg-foreground/5 border border-foreground/10"
              }`}
            >
              Todas
            </Button>
            <Button
              onPress={() => setFilter("pending")}
              className={`px-4 py-2 rounded-lg text-sm transition-all font-normal  ${
                filter === "pending"
                  ? "bg-primary text-white shadow-lg shadow-primary/30"
                  : "bg-background/50 hover:bg-foreground/5 border border-foreground/10"
              }`}
            >
              Pendentes
            </Button>
            <Button
              onPress={() => setFilter("approved")}
              className={`px-4 py-2 rounded-lg text-sm transition-all font-normal  ${
                filter === "approved"
                  ? "bg-primary text-white shadow-lg shadow-primary/30"
                  : "bg-background/50 hover:bg-foreground/5 border border-foreground/10"
              }`}
            >
              Aprovadas
            </Button>
          </div>
        </div>
      </div>

      {/* Lista */}
      <div className="divide-y divide-foreground/10">
        {payments.length === 0 ? (
          <div className="p-12 text-center text-foreground/50">
            <FileText className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p className="text-lg font-medium">Nenhuma fatura encontrada</p>
            <p className="text-sm mt-2">Suas faturas aparecerão aqui</p>
          </div>
        ) : (
          payments.map((payment) => (
            <div key={payment._id} className="p-5">
              <div className="flex flex-col md:flex-row md:items-start md:justify-between md:gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold text-lg">
                      {payment.plan?.name || "Plano"}
                    </h3>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-foreground/60">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {payment.plan?.months || 1} {payment.plan?.months === 1 ? "mês" : "meses"}
                    </span>
                    <span className="w-1 h-1 rounded-full bg-foreground/30"></span>
                    <span>PIX</span>
                    <span className="w-1 h-1 rounded-full bg-foreground/30"></span>
                    <span>{new Date(payment.createdAt).toLocaleDateString("pt-BR", { day: '2-digit', month: 'short', year: 'numeric' })}</span>
                  </div>
                  {payment.efiId && (
                    <div className="mt-2">
                      <span className="text-xs font-mono text-foreground/40 bg-foreground/5 px-2 py-1 rounded">
                        ID: {payment.efiId.substring(0, 12)}...
                      </span>
                    </div>
                  )}
                </div>

                <div className="md:text-right flex flex-col items-start md:items-end mt-2 md:mt-0">
                  <div className="text-2xl font-bold text-primary">
                    R$ {payment.priceFinal.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                  </div>
                  {getStatusBadge(payment.status)}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
