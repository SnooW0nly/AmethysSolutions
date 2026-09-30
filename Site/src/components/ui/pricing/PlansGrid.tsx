"use client";

import { Suspense, useEffect, useState } from "react";
import { Button, Chip } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCheck, faFire, faXmark, faGift } from "@fortawesome/free-solid-svg-icons";
import { useAuth } from "@/hooks/useAuth";
import { useRouter, useSearchParams } from "next/navigation";

type Feature = { title: string; unavailable?: boolean };
type PlanOption = { id: string; name: string; value: number; discount?: number; months: number; description?: string };
type Plan = {
  id: string;
  name: string;
  description?: string;
  primary?: boolean;
  isFree?: boolean; // campo já retornado por /api/info/plans
  features: Feature[];
  plans: PlanOption[];
};

function PlansGridInner() {
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [freeDays, setFreeDays] = useState<number | null>(null);
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const ref = searchParams.get("ref");

  useEffect(() => {
    let mounted = true;
    async function fetchPlans() {
      try {
        setLoading(true);
        const res = await fetch("/api/info/plans", { cache: "no-store" });
        if (!res.ok) throw new Error("Erro ao carregar planos");
        const data = await res.json();
        if (!mounted) return;
        setPlans(Array.isArray(data?.plans) ? data.plans : []);
      } catch (err: any) {
        if (!mounted) return;
        setError(err?.message || "Erro ao carregar planos");
        setPlans([]);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchPlans();
    return () => { mounted = false; };
  }, []);

  // Busca duração do free trial — requer auth, só roda se logado
  useEffect(() => {
    if (!user) return;
    fetch("/api/apps/free/check", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        if (data?.config?.durationDays) setFreeDays(data.config.durationDays);
      })
      .catch(() => {});
  }, [user]);

  function getPurchaseUrl(planId: string) {
    const url = `/purchase?plan=${planId}`;
    return ref ? `${url}&ref=${ref}` : url;
  }

  function getFreePlanUrl() {
    return ref ? `/free?ref=${ref}` : "/free";
  }

  return (
    <div className={`w-full gap-6 ${plans && plans.length === 1 ? "flex flex-col md:flex-row" : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 items-stretch"}`}>
      {loading && (
        <>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-48 bg-foreground/5 border border-foreground/10 rounded-3xl animate-pulse" />
          ))}
        </>
      )}

      {!loading && error && (
        <div className="w-full text-sm text-danger-500 bg-danger/10 border border-danger/20 rounded-lg p-3">{error}</div>
      )}

      {!loading && plans && plans.length > 0 &&
        (() => {
          const original = plans.slice();
          const primaryIdx = original.findIndex((p) => !!p.primary);
          let ordered = original;
          if (primaryIdx >= 0 && original.length === 3) {
            const primary = original[primaryIdx];
            const others = original.filter((_, idx) => idx !== primaryIdx);
            ordered = [others[0], primary, others[1]];
          } else if (primaryIdx >= 0 && original.length > 3) {
            ordered = original.filter((_, idx) => idx !== primaryIdx);
            const mid = Math.floor(original.length / 2);
            ordered.splice(mid, 0, original[primaryIdx]);
          }
          return ordered.map((plan: Plan, index: number, arr: Plan[]) => {
            const isSingle = arr.length === 1;
            const isPrimary = !!plan.primary;
            const isRightMostGreen = arr.length >= 3 && index === arr.length - 1;
            const isLeftMostGray = arr.length >= 3 && index === 0;
            const hasFree = !!plan.isFree;
            const firstOption = plan.plans?.[0];
            const price = typeof firstOption?.value === "number" ? firstOption.value : null;
            const period = firstOption
              ? firstOption.description || (firstOption.months === 1 ? "mês" : `${firstOption.months} meses`)
              : "";
            const containerClass = isPrimary
              ? "border-primary/70 bg-primary/5"
              : isRightMostGreen
              ? "border-green-600/70 bg-green-500/5"
              : "border-foreground/10 bg-foreground/2";
            const priceClass = isRightMostGreen ? "text-green-600" : "";
            const buttonColor: "primary" | "success" | "default" = isRightMostGreen ? "success" : (isLeftMostGray ? "default" : "primary");
            const checkIconClass = isRightMostGreen ? "text-green-500" : (isLeftMostGray ? "text-foreground/60" : "text-primary");
            return (
              <div
                key={index}
                className={`relative w-full rounded-3xl border-2 ${containerClass} p-5 shadow-lg transition-all hover:shadow-2xl overflow-hidden ${isSingle ? "flex flex-col md:flex-row gap-6 md:items-start" : "flex flex-col gap-3 h-full"}`}
              >
                {isPrimary && (
                  <div
                    className="absolute -inset-4 z-0 rounded-[2rem] pointer-events-none"
                    style={{
                      background: "radial-gradient(circle at 50% 50%, rgba(88,101,242,0.22) 0%, rgba(88,101,242,0.08) 60%, transparent 100%)",
                      filter: "blur(12px)",
                    }}
                  />
                )}
                {isPrimary && (
                  <Chip className="absolute -top-3 right-4" variant="solid" color="primary" classNames={{ base: "text-xs" }}>
                    <FontAwesomeIcon icon={faFire} className="text-foreground text-[12px]" /> Mais escolhido
                  </Chip>
                )}

                {/* Coluna esquerda: nome + preço + botões */}
                <div className={`relative z-10 flex flex-col gap-3 ${isSingle ? "md:shrink-0 md:w-[240px]" : ""}`}>
                  <div>
                    <h2 className="text-2xl font-bold">{plan.name}</h2>
                    {plan.description && <p className="text-foreground/70 text-sm leading-relaxed line-clamp-3">{plan.description}</p>}
                  </div>
                  <div className="flex flex-row items-end gap-2">
                    <h1 className={`text-4xl font-extrabold ${priceClass}`}>
                      {price !== null ? price.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—"}
                    </h1>
                    <p className="text-foreground/70 text-sm mb-1">{price !== null ? `/${period}` : ""}</p>
                  </div>

                  {/* Botão principal */}
                  <Button
                    className={`relative z-10 w-full rounded-lg font-medium ${(isRightMostGreen || isLeftMostGray) ? "text-white" : ""}`}
                    color={buttonColor}
                    isDisabled={authLoading}
                    onClick={() => {
                      if (!user) {
                        router.push(ref ? `/login?ref=${ref}` : "/login");
                      } else {
                        window.location.href = getPurchaseUrl(plan.id);
                      }
                    }}
                  >
                    Escolher plano
                  </Button>

                  {/* Botão "Teste grátis" — só no plano com isFree: true no banco */}
                  {hasFree && (
                    <Button
                      className="relative z-10 w-full rounded-lg font-medium"
                      variant="bordered"
                      color="success"
                      isDisabled={authLoading}
                      startContent={<FontAwesomeIcon icon={faGift} className="text-[12px]" />}
                      onClick={() => {
                        if (!user) {
                          router.push(ref ? `/login?ref=${ref}` : "/login");
                        } else {
                          window.location.href = getFreePlanUrl();
                        }
                      }}
                    >
                      Teste grátis{freeDays ? ` · ${freeDays} dias` : ""}
                    </Button>
                  )}
                </div>

                {/* Divisor: vertical no modo horizontal, horizontal no modo vertical */}
                {isSingle
                  ? <>
                      <div className="hidden md:block self-stretch w-px bg-foreground/10 shrink-0" />
                      <hr className="md:hidden my-2 border-foreground/10" />
                    </>
                  : <hr className="my-2 border-foreground/10" />
                }

                {/* Features */}
                <div className={`relative z-10 flex gap-2 ${isSingle ? "flex-col md:flex-row md:flex-wrap md:flex-1 md:min-w-0 md:content-start" : "flex-col"}`}>
                  {plan.features?.map((feature, idx) => (
                    <div key={idx} className={`flex items-center gap-2 ${isSingle ? "md:basis-[calc(50%-0.5rem)] min-w-0" : ""}`}>
                      {feature?.unavailable ? (
                        <>
                          <FontAwesomeIcon icon={faXmark} className="text-danger-500 text-[12px]" />
                          <p className="text-foreground/80 text-sm truncate">{feature.title}</p>
                        </>
                      ) : (
                        <>
                          <FontAwesomeIcon icon={faCheck} className={`${checkIconClass} text-[12px] shrink-0`} />
                          <p className="text-foreground/70 text-sm truncate">{feature.title}</p>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          });
        })()}
    </div>
  );
}

export function PlansGrid() {
  return (
    <Suspense fallback={
      <div className="w-full gap-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-48 bg-foreground/5 border border-foreground/10 rounded-3xl animate-pulse" />
        ))}
      </div>
    }>
      <PlansGridInner />
    </Suspense>
  );
}
