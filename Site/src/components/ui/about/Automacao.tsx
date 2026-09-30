"use client";

import { Link } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChartSimple, faChevronRight, faLocationArrow, faArrowsRotate } from "@fortawesome/free-solid-svg-icons";

export function AutomacaoSection() {
  return (
    <section className="w-full mt-30">
      <div>
        <div className="flex items-center gap-1">
          <FontAwesomeIcon icon={faLocationArrow} className="text-primary text-[12px]" />
          <span className="text-primary/50 text-[12px]">|</span>
          <span className="text-primary font-semibold text-[12px]">Automação Avançada</span>
        </div>
        <h1 className="text-4xl font-bold max-w-2xl my-1 mt-2">Seu servidor no piloto automático</h1>
        <div className="relative">
          <div className="pointer-events-none absolute top-0 left-0 h-20 w-1/2 max-w-sm rounded-full bg-primary/10 blur-[64px]" />
          <p className="text-foreground/70 text-sm max-w-2xl">
            <span className="font-semibold text-primary">Um sistema feito para te ajudar.</span>
            <br />
            O Amethys Pro elimina a necessidade de microgestão no dia a dia do seu servidor. Com sistemas inteligentes de automação, ele assume tarefas repetitivas e mantém tudo funcionando de forma organizada.
          </p>
        </div>
        <Link
          href="/pricing"
          className="text-foreground flex items-center gap-1 w-fit px-4 py-1 bg-foreground/2 border border-foreground/10 rounded-lg hover:bg-foreground/10 duration-100 transition-all cursor-pointer my-2"
        >
          <span className="text-[12px] text-foreground/80">Aprimore seu negócio</span>
          <FontAwesomeIcon icon={faChevronRight} className="text-foreground/70 text-[12px]" />
        </Link>
      </div>

      <div className="border-t border-b border-foreground/10 flex flex-col md:flex-row justify-between mt-5">
        <div className="w-full py-10 flex flex-col gap-1 justify-between">
          <h1 className="text-xl font-semibold">Automação inteligente ao seu alcance</h1>
          <p className="text-foreground/70 text-sm max-w-[500px]">
            Com recursos avançados de automação, nosso bot executa tarefas repetitivas e garante que seus processos permaneçam sempre organizados.
            Concentre-se no que realmente importa enquanto o bot cuida dos detalhes operacionais.
          </p>
          <Link href="/tutorials" className="flex flex-row items-center gap-4 p-4 bg-foreground/2 border border-foreground/10 rounded-lg hover:bg-foreground/5 duration-100 transition-all cursor-pointer my-2 w-[100%] md:w-[95%] leading-relaxed justify-between">
            <div className="flex flex-row items-center gap-4">
              <FontAwesomeIcon icon={faArrowsRotate} className="text-primary text-[15px] flex items-center justify-center p-4 bg-foreground/4 border border-foreground/10 rounded-lg" />
              <div className="flex flex-col items-start">
                <span className="text-foreground/100 text- font-semibold">Aprenda a usar</span>
                <span className="text-[12px] text-foreground/80">Saiba mais como as automações funcionam</span>
              </div>
            </div>
            <div>
              <FontAwesomeIcon icon={faChevronRight} className="text-foreground/70 text-[12px]" />
            </div>
          </Link>
        </div>

        <div className="border-l border-foreground/10 hidden md:block" />
        <div className="border-t border-foreground/10 block md:hidden" />

        <div className="w-full py-10 pl-0 md:pl-10 flex flex-col justify-between">
          <h1 className="text-xl font-semibold">Fluxo sempre sob controle</h1>
          <p className="text-foreground/70 text-sm max-w-[500px]">
            Nosso bot acompanha continuamente o desempenho do seu negócio, garantindo eficiência e alta performance para que você dedique sua atenção a outras áreas estratégicas.
            Com operações personalizáveis, sua empresa se torna mais produtiva e rentável sem esforço adicional.
          </p>
          <Link href="/tutorials" className="flex flex-row items-center gap-4 p-4 bg-foreground/2 border border-foreground/10 rounded-lg hover:bg-foreground/5 duration-100 transition-all cursor-pointer my-2 w-[100%] md:w-[95%] leading-relaxed justify-between">
            <div className="flex flex-row items-center gap-4">
              <FontAwesomeIcon icon={faChartSimple} className="text-primary text-[15px] flex items-center justify-center p-4 bg-foreground/4 border border-foreground/10 rounded-lg" />
              <div className="flex flex-col items-start">
                <span className="text-foreground/100 text- font-semibold">Aprenda a usar</span>
                <span className="text-[12px] text-foreground/80">Saiba mais como as estatísticas funcionam</span>
              </div>
            </div>
            <div>
              <FontAwesomeIcon icon={faChevronRight} className="text-foreground/70 text-[12px]" />
            </div>
          </Link>
        </div>
      </div>
    </section>
  );
}


