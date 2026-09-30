"use client";

import { Card, CardBody, Progress } from "@heroui/react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import StepProgress from "@/components/ui/purchase/pix/StepProgress";
import QrInstructions from "@/components/ui/purchase/pix/QrInstructions";
import ExpiredView from "@/components/ui/purchase/pix/ExpiredView";
import PaymentHeader from "@/components/ui/purchase/pix/PaymentHeader";
import { PaymentCancelled, PaymentLoadError, PaymentLoadingSkeleton } from "@/components/ui/purchase/pix/PaymentStates";
import { PaymentApprovedReceipt } from "@/components/ui/purchase/pix/PaymentApproved";
import PurchaseSummary from "@/components/ui/purchase/pix/PurchaseSummary";
import { usePayment } from "@/hooks/usePayment";

export default function PaymentClient({ paymentId }: { paymentId: string }) {
  const router = useRouter();
  const {
    data,
    status,
    loading,
    loadError,
    notFound,
    progress,
    minutes,
    seconds,
    imgSrc,
    isExpired,
  } = usePayment(paymentId);

  // Redirect to 404 if not found or not owned (defer navigation to effect)
  useEffect(() => {
    if (!notFound) return;
    if (typeof window === "undefined") return;
    const u = new URL(window.location.href);
    u.searchParams.set("nf", "1");
    router.replace(u.toString());
  }, [notFound, router]);

  if (notFound) return null;

  if (isExpired) return <ExpiredView planId={data?.plan.id} />;

  if (status === "approved" && data) {
    return (
      <main className="min-h-[60vh] flex items-center justify-center py-8">
            <div className="p-6 bg-foreground/2 border border-foreground/10 rounded-xl w-full max-w-3xl">
              <PaymentApprovedReceipt
                planName={data.plan.name}
                months={data.plan.months ?? null}
                originalPrice={data.plan.price}
                discountPercent={data.coupon?.discountPercent ?? null}
                finalPrice={data.priceFinal}
                paymentId={data.id}
                createdAt={data.createdAt}
                applicationId={data.applicationId}
              />
            </div>
      </main>
    );
  }

  return (
    <>
      <StepProgress steps={["Escolher plano", "Confirmar", "Finalizar pagamento"]} current={3} />

      <main className="flex flex-col lg:flex-row items-stretch gap-5">
      <div className="flex-1 min-w-0">
      <Card className="border border-foreground/10 bg-foreground/2 rounded-xl p-3">
        <PaymentHeader loading={loading} planName={data?.plan.name} minutes={minutes} seconds={seconds} id={data?.id ?? ""} />
        <CardBody className="flex flex-col items-center gap-4">
          <Progress aria-label="Tempo para expirar" value={progress} className="w-full bg-foreground/2" />

          {status === "cancelled" ? (
            <PaymentCancelled planId={data?.plan.id} />
          ) : loading ? (
            <PaymentLoadingSkeleton />
          ) : loadError || !data ? (
            <PaymentLoadError message={loadError || "Falha ao carregar pagamento"} onRetry={() => router.refresh()} />
          ) : (
            <QrInstructions imgSrc={imgSrc} qrText={data.qr_code_text} />
          )}
        </CardBody>
      </Card>
      </div>

      <PurchaseSummary
        loading={loading || !data}
        planName={data?.plan.name}
        months={data?.plan.months ?? null}
        planPrice={data?.plan.price}
        couponCode={data?.coupon?.code ?? null}
        couponDiscount={data?.coupon?.discountPercent ?? null}
        priceFinal={data?.priceFinal}
      />
    </main>
    </>
  );
}


