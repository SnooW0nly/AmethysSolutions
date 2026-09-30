"use client";

import { AboutHero } from "@/components/ui/about/AboutHero";
import { AboutProduct } from "@/components/ui/about/AboutProduct";
import { AutomacaoSection } from "@/components/ui/about/Automacao";
import { CTASection } from "@/components/ui/home/CTA";

export default function About() {
  return (
    <main>
      <AboutHero />
      <AboutProduct />
      <AutomacaoSection />
      <section className="mt-20">
        <CTASection />
      </section>
    </main>
  );
}


