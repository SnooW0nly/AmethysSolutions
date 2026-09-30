"use client";

import React, { useMemo, useState } from "react";
import { PlanVariant } from "@/components/ui/purchase/DurationSelector";
import { Button, Checkbox } from "@heroui/react";
import { type PaymentMethod } from "@/components/ui/purchase/PaymentMethodSelector";
import { PlanInfoCard } from "@/components/ui/purchase/PlanInfoCard";
import { DurationBlock } from "@/components/ui/purchase/DurationBlock";
import { PaymentMethodBlock } from "@/components/ui/purchase/PaymentMethodBlock";
import { OrderSummaryHeader } from "@/components/ui/purchase/OrderSummaryHeader";
import { CouponForm } from "@/components/ui/purchase/CouponForm";
import { PlanAddonSelector } from "@/components/ui/purchase/PlanAddonSelector";
import { useRouter } from "next/navigation";
import { useAffiliateTracking, getStoredAffiliateCode, clearAffiliateCode } from "@/hooks/useAffiliateTracking";

export function PurchaseClient({
  plan,
}: {
  plan: {
    id: string;
    name: string;
    description: string;
    primary?: boolean;
    features: { title: string }[];
    plans: PlanVariant[];
  };
}) {
  const router = useRouter();

  useAffiliateTracking();

  const defaultId = plan.plans?.[0]?.id ?? "";
  const [selectedId, setSelectedId] = useState<string>(defaultId);

  const selectedVariant = useMemo(
    () => (plan.plans?.find((p) => p.id === selectedId) ?? plan.plans?.[0] ?? null),
    [plan.plans, selectedId]
  );

  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("pix");
  const [isChecked, setIsChecked] = useState(false);

  type AppliedCoupon = { name: string; percent: number } | null;
  const [couponCode, setCouponCode] = useState("");
  const [couponError, setCouponError] = useState<string | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  const [coupon, setCoupon] = useState<AppliedCoupon>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // ── Addons ────────────────────────────────────────────────────────────────
  const [selectedAddons, setSelectedAddons] = useState<string[]>([]);
  const [addonExtraTotal, setAddonExtraTotal] = useState(0);

  const handleAddonToggle = (addonId: string, extraValue: number, selected: boolean) => {
    setSelectedAddons((prev) => {
      const next = selected ? [...prev, addonId] : prev.filter((id) => id !== addonId);
      // Recalcula total de addons
      setAddonExtraTotal((t) => selected ? t + extraValue : t - extraValue);
      return next;
    });
  };

  // ── Cupom ──────────────────────────────────────────────────────────────────
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
        body: JSON.stringify({ name: code, cartTotal: selectedVariant?.value ?? 0 }),
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

  // ── Preço final ─────────────────────────────────────────────────────────────
  const finalPrice = useMemo(() => {
    if (!selectedVariant) return 0;
    const base = selectedVariant.value + addonExtraTotal;
    if (!coupon) return Number(base.toFixed(2));
    const off = Math.max(0, Math.min(100, coupon.percent));
    return Number((base * (1 - off / 100)).toFixed(2));
  }, [selectedVariant, coupon, addonExtraTotal]);

  const originalValue = useMemo(
    () => (selectedVariant ? selectedVariant.value + addonExtraTotal : 0),
    [selectedVariant, addonExtraTotal]
  );

  // ── Finalizar ────────────────────────────────────────────────────────────────
  async function handleFinalizePurchase() {
    if (!isChecked || isCreating) return;
    setCreateError(null);
    setIsCreating(true);
    try {
      const affiliateCode = getStoredAffiliateCode();

      const res = await fetch("/api/payment/create", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          planId: plan.id,
          monthId: selectedVariant?.id,
          couponCode: coupon?.name ?? undefined,
          affiliateCode: affiliateCode || undefined,
          addons: selectedAddons,
        }),
      });

      const data = await res.json().catch(() => null);
      if (!res.ok || !data?.id) {
        throw new Error(data?.error || "Falha ao criar pagamento");
      }

      clearAffiliateCode();
      router.push(`/purchase/${data.id}`);
    } catch (err: any) {
      setCreateError(String(err?.message || "Erro inesperado"));
    } finally {
      setIsCreating(false);
    }
  }

  if (!selectedVariant) {
    return (
      <main className="flex flex-col gap-4">
        <div className="rounded-lg border border-foreground/10 bg-foreground/2 p-4">
          <h1 className="text-xl font-semibold">Plano indisponível</h1>
          <p className="text-sm text-foreground/70">
            Este plano não possui opções de duração configuradas no momento.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-col lg:flex-row justify-between gap-6 lg:gap-10">
      <div className="flex flex-col gap-2 lg:w-3/4 w-full">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold">Finalizar compra</h1>
          <p className="text-foreground/70 text-sm">
            Antes de finalizar a compra, confira as informações do plano e os métodos de
            pagamento disponíveis.
          </p>
        </div>

        <hr className="my-2 border-foreground/10" />

        <PlanInfoCard
          name={plan.name}
          description={plan.description}
          selectedVariant={selectedVariant}
          coupon={coupon}
          finalPrice={finalPrice}
        />

        <DurationBlock
          variants={plan.plans}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />

        {/* Addons */}
        <PlanAddonSelector
          planId={plan.id}
          selectedAddons={selectedAddons}
          onToggle={handleAddonToggle}
        />

        <PaymentMethodBlock value={paymentMethod} onChange={setPaymentMethod} />
      </div>

      <aside className="flex flex-col gap-2 lg:w-1/2 w-full bg-foreground/2 p-4 rounded-lg border border-foreground/10 justify-end">
        <OrderSummaryHeader
          originalValue={originalValue}
          finalPrice={finalPrice}
          description={selectedVariant.description}
          hasDiscount={!!selectedVariant.discount || addonExtraTotal > 0}
          couponPercent={coupon?.percent ?? null}
          paymentMethod={paymentMethod}
        />
        {addonExtraTotal > 0 && (
          <p className="text-xs text-foreground/50">
            Inclui adicionais:{" "}
            <span className="text-primary font-medium">+R$ {addonExtraTotal.toFixed(2)}</span>
          </p>
        )}
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
            classNames={{
              base: "flex items-start justify-start",
              label: "text-left",
              wrapper: "mt-0.5",
            }}
            isSelected={isChecked}
            onValueChange={setIsChecked}
          >
            <p className="text-sm text-foreground/80">
              Ao finalizar a compra, eu concordo com nossas políticas de reembolso e privacidade
              de dados estabelecidas, e{" "}
              <span className="font-semibold">respeito nossa política de cancelamento.</span>
            </p>
          </Checkbox>
          {createError ? <p className="text-sm text-danger">{createError}</p> : null}
          <Button
            color="primary"
            className="w-full self-end"
            isDisabled={!isChecked || isCreating}
            isLoading={isCreating}
            onPress={handleFinalizePurchase}
          >
            Finalizar compra
          </Button>
        </div>
      </aside>
    </main>
  );
}
