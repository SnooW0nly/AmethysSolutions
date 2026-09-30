"use client"

import { PlansGrid } from "@/components/ui/pricing/PlansGrid"
import { PricingFeatures } from "@/components/ui/pricing/PricingFeatures"
import { FAQ } from "@/components/ui/pricing/FAQ"
import { PartnersMarquee } from "@/components/ui/pricing/PartnersMarquee"

export default function Pricing() {
    return (
        <main>
            <section className="flex flex-col items-center justify-center gap-10">
                <div className="flex flex-col gap-2 text-center">
                    <h1 className="text-5xl font-bold">Planos e preços</h1>
                    <p className="text-foreground/70 text-lg">Escolha o plano que melhor atende às suas necessidades.</p>
                </div>
                <PlansGrid />
            </section>
            <hr className="my-10 border-foreground/10" />
            <PricingFeatures />
            <FAQ />
            {/* Carrossel de parceiros — só renderiza se houver parceiros ativos */}
            <PartnersMarquee />
        </main>
    )
}