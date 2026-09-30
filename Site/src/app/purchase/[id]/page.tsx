import { notFound } from "next/navigation";
import PaymentClient from "./payment-client";

type PageProps = { params: Promise<{ id: string }>; searchParams?: Promise<Record<string, string>> };

export default async function PurchasePaymentPage({ params, searchParams }: PageProps) {
  const { id } = await params;
  const sp = (await searchParams) || {};
  if (sp.nf === "1") notFound();
  return <PaymentClient paymentId={id} />;
}


