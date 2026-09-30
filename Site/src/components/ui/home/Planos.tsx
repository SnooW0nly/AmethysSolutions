"use client";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { features } from "@/config/features";

export function PlanosSection() {
  return (
    <section className="mt-30 md:mt-40 w-full">
      <div className="bg-foreground/1 border border-foreground/10 p-5 md:p-10 rounded-xl">
        <div className="flex flex-col gap-2">
          <h1 className="text-4xl font-bold max-w-2xl">
            Preços acessíveis e <span className="text-primary">planos flexíveis</span>
          </h1>
          <p className="text-foreground/70 text-sm max-w-2xl">
            Chega de pagar caro por soluções complexas. Nossa plataforma oferece valores justos e opções que se adaptam ao seu momento.
          </p>
          <hr className="border-foreground/10 my-3" />
          <div className="flex flex-col">
            <p className="text-primary text-[12px]">Com a Amethys você paga apenas</p>
            <p className="text-primary text-3xl font-bold">
              R$15,00
              <span className="text-foreground/60 text-[12px] font-[300]">/ mês</span>
            </p>
            <p className="text-foreground/70 text-sm max-w-2xl">
              Sem custos extras, sem complicações. Apenas resultados reais e práticos para o seu negócio.
            </p>
          </div>
          <div className="flex flex-col md:flex-row gap-2">
            <div className="bg-primary/10 border border-primary/20 rounded-full px-3 py-1 text-sm text-primary w-fit">
              Experimente grátis
            </div>
            <div className="bg-primary/10 border border-primary/20 rounded-full px-3 py-1 text-sm text-primary w-fit">
              Descontos de até 20%
            </div>
          </div>
          <hr className="border-foreground/10 my-3" />
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
            {features.map((feature, index) => (
              <div key={index} className="flex flex-col gap-1 max-w-sm md:max-w-2xs">
                <div className="flex gap-1 items-center">
                  <FontAwesomeIcon icon={feature.icon} className="text-[12px]" />
                  <span className="text-[0.875rem]">{feature.title}</span>
                </div>
                <p className="text-foreground/70 font-[370] text-[13px] leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}


