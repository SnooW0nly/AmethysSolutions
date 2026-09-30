"use client";

import { useState, useEffect } from "react";
import { RefreshCw, Clock, AlertCircle, CheckCircle2, Copy } from "lucide-react";

interface RenewalSectionProps {
  applicationId: string;
}

interface Application {
  _id: string;
  name: string;
  plan: {
    id: string;
    name: string;
  };
  expiresAt: string;
}

interface Plan {
  id: string;
  name: string;
  plans: {
    id: string;
    name: string;
    months: number;
    value: number;
    discount: number;
  }[];
}

export default function RenewalSection({ applicationId }: RenewalSectionProps) {
  const [application, setApplication] = useState<Application | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [selectedMonths, setSelectedMonths] = useState<number>(1);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [payment, setPayment] = useState<any>(null);
  const [copiedPix, setCopiedPix] = useState(false);

  useEffect(() => {
    loadApplication();
  }, [applicationId]);

  const loadApplication = async () => {
    try {
      // Busca a aplicação
      const appResponse = await fetch(`/api/applications/${applicationId}`, {
        credentials: "include",
      });

      if (!appResponse.ok) {
        console.error("[RenewalSection] Erro HTTP ao buscar app:", appResponse.status);
        try {
          const errorData = await appResponse.json();
          console.error("[RenewalSection] Erro:", errorData.message);
          alert(`Erro ao buscar aplicação: ${errorData.message}`);
        } catch {
          const text = await appResponse.text();
          console.error("[RenewalSection] Resposta:", text.substring(0, 200));
          alert(`Erro ao buscar aplicação (${appResponse.status})`);
        }
        return;
      }

      const appData = await appResponse.json();
      
      if (appData.success && appData.data) {
        setApplication(appData.data);

        // Cria plano baseado nos dados da aplicação
        const basePrice = appData.data.plan.price || 50;
        const fallbackPlan: Plan = {
          id: appData.data.plan.id,
          name: appData.data.plan.name || "Plano",
          plans: [
            { id: "1m", name: "1 Mês", months: 1, value: basePrice, discount: 0 },
            { id: "3m", name: "3 Meses", months: 3, value: Math.round(basePrice * 3 * 0.9), discount: 10 },
            { id: "6m", name: "6 Meses", months: 6, value: Math.round(basePrice * 6 * 0.85), discount: 15 },
          ],
        };
        setPlan(fallbackPlan);
        setSelectedMonths(appData.data.plan.months || 1);
      }
    } catch (error) {
      console.error("[RenewalSection] Erro ao carregar aplicação:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRenewal = async () => {
    setCreating(true);
    try {
      const response = await fetch("/api/invoices/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          applicationId,
          months: selectedMonths,
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        setPayment(data.data.payment);
      } else {
        alert(`Erro: ${data.message}`);
      }
    } catch (error) {
      console.error("Erro ao criar renovação:", error);
      alert("Erro ao criar renovação");
    } finally {
      setCreating(false);
    }
  };

  const copyPixCode = () => {
    if (payment?.pixCode) {
      navigator.clipboard.writeText(payment.pixCode);
      setCopiedPix(true);
      setTimeout(() => setCopiedPix(false), 2000);
    }
  };

  const selectedPlanOption = plan?.plans.find((p) => p.months === selectedMonths);
  const daysLeft = application
    ? Math.ceil((new Date(application.expiresAt).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    : 0;

  if (loading) {
    return null; // Não mostra loading, deixa a página principal controlar
  }

  if (!application || !plan) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <p className="text-red-500 font-medium">
              {!application ? "Aplicação não encontrada" : "Plano não encontrado"}
            </p>
          </div>
          <p className="text-sm text-foreground/60">
            {!application 
              ? "Esta aplicação não existe ou você não tem permissão para acessá-la."
              : "O plano desta aplicação não está mais disponível. Entre em contato com o suporte."}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => window.location.href = "/dashboard"}
              className="px-4 py-2 bg-foreground/10 hover:bg-foreground/20 rounded-lg text-sm font-medium transition-colors"
            >
              Voltar ao Dashboard
            </button>
            <button
              onClick={() => window.location.href = "/dashboard/invoices"}
              className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Ver Minhas Faturas
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-primary/10 rounded-xl">
          <RefreshCw className="w-6 h-6 text-primary" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-primary">Renovar Aplicação</h2>
          <p className="text-sm text-foreground/60">
            {application.name} • {application.plan.name}
          </p>
        </div>
      </div>

      {/* Status de vencimento */}
      <div className={`p-4 rounded-xl mb-6 ${daysLeft <= 3 ? "bg-red-500/10 border border-red-500/20" : "bg-yellow-500/10 border border-yellow-500/20"}`}>
        <div className="flex items-center gap-2">
          <Clock className={`w-5 h-5 ${daysLeft <= 3 ? "text-red-500" : "text-yellow-500"}`} />
          <p className={`font-medium ${daysLeft <= 3 ? "text-red-500" : "text-yellow-500"}`}>
            {daysLeft > 0 ? `Vence em ${daysLeft} ${daysLeft === 1 ? "dia" : "dias"}` : "Vencido"}
          </p>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Data de vencimento: {new Date(application.expiresAt).toLocaleDateString()}
        </p>
      </div>

      {!payment ? (
        <>
          {/* Seleção de plano */}
          <div className="mb-6">
            <label className="block text-sm font-medium mb-3">Selecione o período de renovação:</label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {plan.plans.map((planOption) => (
                <button
                  key={planOption.id}
                  onClick={() => setSelectedMonths(planOption.months)}
                  className={`p-4 rounded-xl border-2 transition-all ${
                    selectedMonths === planOption.months
                      ? "border-primary bg-primary/10 shadow-lg shadow-primary/20"
                      : "border-foreground/10 hover:border-primary/50 bg-background/30"
                  }`}
                >
                  <div className="text-lg font-bold">{planOption.months} {planOption.months === 1 ? "mês" : "meses"}</div>
                  <div className="text-2xl font-bold text-primary mt-1">
                    R$ {planOption.value.toFixed(2)}
                  </div>
                  {planOption.discount > 0 && (
                    <div className="text-xs text-green-500 mt-1">
                      {planOption.discount}% de desconto
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Resumo */}
          {selectedPlanOption && (
            <div className="bg-foreground/5 rounded-xl p-4 mb-6 border border-foreground/10">
              <h3 className="font-medium mb-2">Resumo da Renovação</h3>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Período:</span>
                  <span>{selectedPlanOption.months} {selectedPlanOption.months === 1 ? "mês" : "meses"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Valor:</span>
                  <span className="font-bold text-primary">R$ {selectedPlanOption.value.toFixed(2)}</span>
                </div>
                <div className="flex justify-between pt-2 border-t border-border">
                  <span className="text-muted-foreground">Nova data de vencimento:</span>
                  <span>
                    {new Date(
                      new Date(application.expiresAt).getTime() + selectedPlanOption.months * 30 * 24 * 60 * 60 * 1000
                    ).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Botão de criar renovação */}
          <button
            onClick={handleCreateRenewal}
            disabled={creating}
            className="w-full px-6 py-3 bg-primary hover:bg-primary/90 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all shadow-lg shadow-primary/30 hover:shadow-xl hover:shadow-primary/40 flex items-center justify-center gap-2"
          >
            {creating ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Gerando Pagamento...
              </>
            ) : (
              <>
                <RefreshCw className="w-5 h-5" />
                Gerar Pagamento PIX
              </>
            )}
          </button>
        </>
      ) : (
        /* Pagamento gerado */
        <div className="space-y-4">
          <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-green-500">Pagamento gerado com sucesso!</p>
              <p className="text-sm text-muted-foreground mt-1">
                Escaneie o QR Code ou copie o código PIX para realizar o pagamento
              </p>
            </div>
          </div>

          {/* QR Code */}
          {payment.pixQrCode && (
            <div className="flex justify-center p-6 bg-white rounded-xl shadow-lg">
              <img src={payment.pixQrCode} alt="QR Code PIX" className="w-64 h-64" />
            </div>
          )}

          {/* Código PIX */}
          <div>
            <label className="block text-sm font-medium mb-2">Código PIX Copia e Cola:</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={payment.pixCode}
                readOnly
                className="flex-1 px-4 py-3 bg-background/50 border border-foreground/10 rounded-xl font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                onClick={copyPixCode}
                className="px-4 py-3 bg-primary hover:bg-primary/90 rounded-xl transition-all shadow-lg shadow-primary/30"
              >
                {copiedPix ? <CheckCircle2 className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {/* Informações */}
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-muted-foreground">
                <p>• O pagamento será processado automaticamente após a confirmação</p>
                <p>• A renovação será aplicada assim que o pagamento for aprovado</p>
                <p>• Este código PIX expira em 30 minutos</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
