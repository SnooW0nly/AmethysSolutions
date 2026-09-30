"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { DashboardHeader } from "@/components/ui/dashboard/DashboardHeader";
import { Loading } from "@/components/Loading";
import { useRequireAuth } from "@/hooks/useAuth";
import RenewalPayment from "@/components/ui/dashboard/invoices/RenewalPayment";
import InvoicesList from "@/components/ui/dashboard/invoices/InvoicesList";
import ExpiringApplications from "@/components/ui/dashboard/invoices/ExpiringApplications";

function InvoicesContent() {
    const { user, loading } = useRequireAuth();
    const searchParams = useSearchParams();
    const renewAppId = searchParams.get("renew");
  
    if (loading) return <Loading />;

    // Se tem parâmetro renew, mostra apenas a página de pagamento
    if (renewAppId) {
        return (
            <main className="min-h-screen bg-gradient-to-b from-background to-background/50 py-12 px-4">
                <RenewalPayment applicationId={renewAppId} />
            </main>
        );
    }

    // Senão, mostra a lista de faturas e apps expirando
    return (
        <main>
            {user && <DashboardHeader user={user} />}
            <section className="w-full flex flex-col gap-4">
                {/* Aplicações expirando (7 dias ou menos) */}
                <ExpiringApplications />

                {/* Lista de faturas */}
                <InvoicesList />
            </section>
        </main>
    )
}

export default function Invoices() {
    return (
        <Suspense fallback={<Loading />}>
            <InvoicesContent />
        </Suspense>
    );
}