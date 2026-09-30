"use client";

import { Hero } from "@/components/ui/home/Hero";
import { Preview } from "@/components/ui/home/Preview";
import { StatsSection } from "@/components/ui/home/Stats";
import { MonetizacaoSection } from "@/components/ui/home/Monetizacao";
import { PersonalizacaoSegurancaSection } from "@/components/ui/home/PersonalizacaoSeguranca";
import { PlanosSection } from "@/components/ui/home/Planos";
import { InfraestruturaSection } from "@/components/ui/home/Infraestrutura";
import { SaibaMaisSection } from "@/components/ui/home/SaibaMais";
import { CTASection } from "@/components/ui/home/CTA";

export default function Home() {
  return (
    <main className="flex flex-col mt-[-30] md:mt-0">
      <Hero />
      <Preview />
      {/* <StatsSection /> */}
      <InfraestruturaSection />
      <PersonalizacaoSegurancaSection />
      <SaibaMaisSection />
      <CTASection />
    </main>
  );
}