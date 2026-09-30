"use client";

import React, { useMemo, useState, useEffect, useRef } from "react";
import { PlanVariant } from "@/components/ui/purchase/DurationSelector";
import { Button, Checkbox } from "@heroui/react";
import { type PaymentMethod } from "@/components/ui/purchase/PaymentMethodSelector";
import { PlanInfoCard } from "@/components/ui/purchase/PlanInfoCard";
import { DurationBlock } from "@/components/ui/purchase/DurationBlock";
import { PaymentMethodBlock } from "@/components/ui/purchase/PaymentMethodBlock";
import { OrderSummaryHeader } from "@/components/ui/purchase/OrderSummaryHeader";
import { CouponForm } from "@/components/ui/purchase/CouponForm";
import { Check, ArrowRight, Copy, AlertCircle } from "lucide-react";
import { Card, CardBody, CardHeader, Progress } from "@heroui/react";
import { useRouter } from "next/navigation";

interface RenewalPaymentProps {
  applicationId: string;
}

interface Application {
  _id: string;
  name: string;
  plan: {
    id: string;
    name: string;
    price: number;
    months: number;
  };
  expiresAt: string;
}

type PaymentStatus = "pending" | "approved" | "cancelled";

export default function RenewalPayment({ applicationId }: RenewalPaymentProps) {
  const router = useRouter();
  const [application, setApplication] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string>("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("pix");
  const [isChecked, setIsChecked] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  
  type AppliedCoupon = { name: string; percent: number } | null;
  const [couponCode, setCouponCode] = useState("");
  const [couponError, setCouponError] = useState<string | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  const [coupon, setCoupon] = useState<AppliedCoupon>(null);
  
  const [payment, setPayment] = useState<any>(null);
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus>("pending");
  const [timeLeft, setTimeLeft] = useState<number>(0);
  const [now, setNow] = useState<number>(Date.now());
  const [copiedPix, setCopiedPix] = useState(false);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  
  const [planOptions, setPlanOptions] = useState<PlanVariant[]>([]);

  const selectedVariant = useMemo(
    () => (planOptions?.find((p) => p.id === selectedId) ?? planOptions?.[0] ?? null),
    [planOptions, selectedId],
  );

  const finalPrice = useMemo(() => {
    if (!selectedVariant) return 0;
    if (!coupon) return selectedVariant.value;
    const off = Math.max(0, Math.min(100, coupon.percent));
    return Number((selectedVariant.value * (1 - off / 100)).toFixed(2));
  }, [selectedVariant, coupon]);

  const progress = useMemo(() => {
    const total = 10 * 60;
    const clamped = Math.max(0, Math.min(total, timeLeft));
    return 100 - Math.round((clamped / total) * 100);
  }, [timeLeft]);

  const imgSrc = useMemo(() => {
    const s = payment?.pixQrCode || "";
    if (!s) return null;
    return s.startsWith("data:") ? s : `data:image/png;base64,${s}`;
  }, [payment?.pixQrCode]);

  useEffect(() => {
    loadApplication();
  }, [applicationId]);

  useEffect(() => {
    if (planOptions.length > 0 && !selectedId) {
      setSelectedId(planOptions[0].id);
    }
  }, [planOptions, selectedId]);

  // Update timer every second
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Calculate time left
  useEffect(() => {
    if (payment?.expiresAt) {
      const expires = new Date(payment.expiresAt).getTime();
      const diff = Math.max(0, expires - now);
      setTimeLeft(Math.floor(diff / 1000));
    }
  }, [payment, now]);

  // Poll payment status every 5s while pending
  useEffect(() => {
    if (!payment?.id || paymentStatus !== "pending") {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }

    async function pollStatus() {
      try {
        const res = await fetch(`/api/payment/${payment.id}/status`, {
          credentials: "include",
          cache: "no-store",
        });
        const data = await res.json().catch(() => null);
        if (data?.status && isMounted) {
          setPaymentStatus(data.status as PaymentStatus);
        }
      } catch (error) {
        console.error("Error polling payment status:", error);
      }
    }

    let isMounted = true;
    pollStatus();
    pollRef.current = setInterval(pollStatus, 5000);

    return () => {
      isMounted = false;
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [payment?.id, paymentStatus]);

  const loadApplication = async () => {
    try {
      const appResponse = await fetch(`/api/applications/${applicationId}`, {
        credentials: "include",
      });

      if (!appResponse.ok) {
        alert("Erro ao buscar aplicação");
        return;
      }

      const appData = await appResponse.json();
      
      if (appData.success && appData.data) {
        setApplication(appData.data);
        
        const plansResponse = await fetch("/api/info/plans", {
          credentials: "include",
        });
        
        if (plansResponse.ok) {
          const plansData = await plansResponse.json();
          const currentPlan = plansData.plans?.find((p: any) => p.id === appData.data.plan.id);
          
          if (currentPlan?.plans) {
            const variants: PlanVariant[] = currentPlan.plans.map((p: any) => ({
              id: p.id,
              name: p.name,
              value: p.value,
              description: p.description,
              discount: p.discount || 0,
              months: p.months,
            }));
            setPlanOptions(variants);
          }
        }
      }
    } catch (error) {
      console.error("Erro ao carregar aplicação:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyCoupon = async () => {
    if (!couponCode.trim()) {
      setCouponError("Digite um cupom.");
      return;
    }
    setCouponError(null);
    setIsApplying(true);
    try {
      const code = couponCode.trim().toUpperCase();
      const res = await fetch("/api/info/coupons/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: code, cartTotal: selectedVariant?.value ?? 0 })
      });
      const data = await res.json().catch(() => null);
      if (!res.ok || !data?.valid) {
        setCoupon(null);
        setCouponError("Cupom inválido.");
        return;
      }
      setCoupon({ name: data.coupon.name, percent: Number(data.coupon.percent || 0) });
      setCouponError(null);
    } catch {
      setCoupon(null);
      setCouponError("Cupom inválido.");
    } finally {
      setIsApplying(false);
    }
  };

  async function handleFinalizeRenewal() {
    if (!isChecked || isCreating) return;
    setCreateError(null);
    setIsCreating(true);
    try {
      const res = await fetch("/api/invoices/create", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          applicationId,
          months: selectedVariant?.months,
          couponCode: coupon?.name ?? undefined,
        }),
      });

      const data = await res.json().catch(() => null);
      if (!res.ok || !data?.success) {
        throw new Error(data?.message || "Falha ao criar pagamento");
      }

      setPayment(data.data.payment);
    } catch (err: any) {
      setCreateError(String(err?.message || "Erro inesperado"));
    } finally {
      setIsCreating(false);
    }
  }

  const copyPixCode = () => {
    if (payment?.pixCode) {
      navigator.clipboard.writeText(payment.pixCode);
      setCopiedPix(true);
      setTimeout(() => setCopiedPix(false), 2000);
    }
  };

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!application) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <h3 className="text-xl font-bold mb-2">Aplicação não encontrada</h3>
        <p className="text-foreground/60">Esta aplicação não existe ou você não tem permissão.</p>
      </div>
    );
  }

  if (paymentStatus === "approved" && payment) {
    return (
      <main className="min-h-[60vh] flex items-center justify-center py-8">
        <div className="p-6 bg-foreground/2 border border-foreground/10 rounded-xl w-full max-w-3xl">
          <div className="w-full">
            <div className="flex items-center justify-between w-full mb-6">
              <div className="flex flex-col">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center">
                    <Check className="w-6 h-6 text-green-500" />
                  </div>
                  <h3 className="text-2xl font-semibold">Pagamento Aprovado!</h3>
                </div>
                <p className="text-sm text-foreground/60">Sua renovação foi processada com sucesso</p>
              </div>
            </div>
            <hr className="border-foreground/10 my-4" />
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-foreground/70">Aplicação</span>
                <span className="font-medium">{application?.name}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-foreground/70">Plano</span>
                <span className="font-medium">{application?.plan.name}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-foreground/70">Duração renovada</span>
                <span className="font-medium">{selectedVariant?.months || 1} {(selectedVariant?.months || 1) > 1 ? "meses" : "mês"}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-foreground/70">ID do pagamento</span>
                <span className="font-medium font-mono text-xs">#{payment.id}</span>
              </div>
              <hr className="border-foreground/10 my-1" />
              <div className="flex items-center justify-between text-sm">
                <span className="text-foreground/70">Valor pago</span>
                <span className="text-lg font-semibold">{new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(payment.amount || 0))}</span>
              </div>
              <div className="mt-4">
                <Button
                  color="primary"
                  fullWidth
                  className="w-full rounded-lg"
                  onPress={() => {
                    window.location.assign(`/dashboard/app/${applicationId}/overview`);
                  }}
                >
                  Ir para o painel <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (payment) {
    return (
      <main className="flex flex-col lg:flex-row items-stretch gap-5">
        <div className="flex-1 min-w-0">
          <Card className="border border-foreground/10 bg-foreground/2 rounded-xl p-3">
            <CardHeader className="flex items-center justify-between">
              <div className="flex flex-col">
                <h1 className="text-2xl font-semibold">Pagamento PIX - Renovação</h1>
                <p className="text-foreground/70 text-sm">{application?.name} - #{payment.id}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-foreground/70">Tempo restante</p>
                <p className="font-mono">
                  {minutes.toString().padStart(2, "0")}:{seconds.toString().padStart(2, "0")}
                </p>
              </div>
            </CardHeader>
            <CardBody className="flex flex-col items-center gap-4">
              <Progress aria-label="Tempo para expirar" value={progress} className="w-full bg-foreground/2" />

              <div className="w-full flex flex-col lg:flex-row items-start gap-6">
                <div className="rounded-md self-center md:self-start">
                  {imgSrc ? (
                    <img src={imgSrc} alt="QR Code PIX" className="h-56 w-56 rounded-md" />
                  ) : (
                    <div className="h-56 w-56 rounded-md bg-foreground/5 flex items-center justify-center">
                      <p className="text-foreground/40 text-sm">QR Code não disponível</p>
                    </div>
                  )}
                </div>
                <div className="flex-1 w-full max-w-xl">
                  <div className="flex flex-col gap-3">
                    <div className="flex items-start gap-3">
                      <div className="h-7 w-7 rounded-full bg-foreground/10 border border-foreground/10 flex items-center justify-center text-sm font-semibold">1</div>
                      <div>
                        <p className="text-sm font-medium">Abra seu banco</p>
                        <p className="text-xs text-foreground/60">Acesse o aplicativo do seu banco.</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="h-7 w-7 rounded-full bg-foreground/10 border border-foreground/10 flex items-center justify-center text-sm font-semibold">2</div>
                      <div>
                        <p className="text-sm font-medium">Escaneie ou use copia e cola</p>
                        <p className="text-xs text-foreground/60">Escaneie o QR Code ao lado ou copie o código abaixo.</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="h-7 w-7 rounded-full bg-foreground/10 border border-foreground/10 flex items-center justify-center text-sm font-semibold">3</div>
                      <div>
                        <p className="text-sm font-medium">Efetue o pagamento</p>
                        <p className="text-xs text-foreground/60">Confirme o valor e finalize no seu banco.</p>
                      </div>
                    </div>
                    <div className="relative mt-2">
                      <p className="text-xs text-foreground/70 border border-foreground/10 break-all text-left max-w-full p-3 pr-12 bg-foreground/5 rounded-md font-[monospace]">
                        {payment.pixCode || "Código não disponível"}
                      </p>
                      <div className="absolute top-2 right-2">
                        <button
                          onClick={copyPixCode}
                          disabled={!payment.pixCode}
                          className="h-8 w-8 rounded-md bg-foreground/10 hover:bg-foreground/20 disabled:bg-foreground/5 flex items-center justify-center transition-colors"
                          aria-label="Copiar código PIX"
                        >
                          {copiedPix ? (
                            <Check className="w-4 h-4" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>

        <aside className="w-full md:w-1/3">
          <Card className="border border-foreground/10 bg-foreground/2 rounded-xl p-3 h-full flex items-center justify-between flex-col">
            <CardHeader className="pb-0">
              <div className="flex flex-col">
                <h2 className="text-xl font-semibold">Resumo</h2>
                <p className="text-sm text-foreground/60">Veja as informações da renovação e finalize o pagamento seguindo as instruções.</p>
              </div>
            </CardHeader>
            <CardBody className="flex flex-col gap-3">
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Renovação</span>
                    <div className="h-[1px] w-full bg-foreground/10" />
                  </div>
                  <div className="flex items-center gap-2 justify-between">
                    <span className="text-sm text-foreground/70">Aplicação</span>
                    <span className="text-sm font-medium">{application?.name}</span>
                  </div>
                  <div className="flex items-center gap-2 justify-between">
                    <span className="text-sm text-foreground/70">Plano</span>
                    <span className="text-sm font-medium">{application?.plan.name}</span>
                  </div>
                  <div className="flex items-center gap-2 justify-between">
                    <span className="text-sm text-foreground/70">Duração</span>
                    <span className="text-sm font-medium">{selectedVariant?.months || 1} {(selectedVariant?.months || 1) > 1 ? "meses" : "mês"}</span>
                  </div>
                </div>
                <hr className="border-foreground/10" />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground/70">Valor final</span>
                  <span className="text-lg font-semibold">
                    {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(payment.amount || 0))}
                  </span>
                </div>
              </div>
            </CardBody>
          </Card>
        </aside>
      </main>
    );
  }

  if (!selectedVariant) {
    return (
      <main className="flex flex-col gap-4">
        <div className="rounded-lg border border-foreground/10 bg-foreground/2 p-4">
          <h1 className="text-xl font-semibold">Plano indisponível</h1>
          <p className="text-sm text-foreground/70">Este plano não possui opções de duração configuradas no momento.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-col lg:flex-row justify-between gap-6 lg:gap-10">
      <div className="flex flex-col gap-2 lg:w-3/4 w-full">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold">Renovar aplicação</h1>
          <p className="text-foreground/70 text-sm">Escolha o período de renovação para {application.name} e finalize o pagamento.</p>
        </div>

        <hr className="my-2 border-foreground/10" />

        <PlanInfoCard 
          name={application.plan.name} 
          description={`Renovação da aplicação ${application.name}`} 
          selectedVariant={selectedVariant} 
          coupon={null} 
          finalPrice={finalPrice} 
        />

        <DurationBlock variants={planOptions} selectedId={selectedId} onSelect={setSelectedId} />

        <PaymentMethodBlock value={paymentMethod} onChange={setPaymentMethod} />
      </div>

      <aside className="flex flex-col gap-2 lg:w-1/2 w-full bg-foreground/2 p-4 rounded-lg border border-foreground/10 justify-end">
        <OrderSummaryHeader
          originalValue={selectedVariant.value}
          finalPrice={finalPrice}
          description={selectedVariant.description}
          hasDiscount={!!selectedVariant.discount}
          couponPercent={coupon?.percent ?? null}
          paymentMethod={paymentMethod}
        />
        <hr className="my-1 border-foreground/10" />
        <CouponForm
          value={couponCode}
          error={couponError}
          isApplying={isApplying}
          hasApplied={!!coupon}
          onChange={setCouponCode}
          onApply={handleApplyCoupon}
        />
        <hr className="my-2 border-foreground/10" />
        <div className="flex flex-col gap-3 self-end items-end">
          <Checkbox
            size="sm"
            classNames={{ base: "flex items-start justify-start", label: "text-left", wrapper: "mt-0.5" }}
            isSelected={isChecked}
            onValueChange={setIsChecked}
          >
            <p className="text-sm text-foreground/80">Ao finalizar a renovação, eu concordo com as políticas de renovação e <span className="font-semibold">confirmo que desejo adicionar {selectedVariant.months} {selectedVariant.months > 1 ? "meses" : "mês"} à minha aplicação.</span></p>
          </Checkbox>
          {createError ? (
            <p className="text-sm text-danger">{createError}</p>
          ) : null}
          <Button
            color="primary"
            className="w-full self-end"
            isDisabled={!isChecked || isCreating}
            isLoading={isCreating}
            onPress={handleFinalizeRenewal}
          >
            Finalizar renovação
          </Button>
        </div>
      </aside>
    </main>
  );
}
