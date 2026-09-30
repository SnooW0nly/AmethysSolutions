"use client";

import { Link, Tooltip } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChartSimple, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { CustomLineChart } from "@/components/ui/home/Chart";
import { useRef } from "react";

type ChartPoint = { date: string; value: number };

const CHART_DATA: ChartPoint[] = [
  { date: "01 Ago", value: 50 },
  { date: "10 Ago", value: 400 },
  { date: "20 Ago", value: 700 },
  { date: "30 Ago", value: 1200 },
  { date: "10 Set", value: 1800 },
  { date: "20 Set", value: 2200 },
  { date: "30 Set", value: 2500 },
];

export function MonetizacaoSection() {
  const estimativaRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<HTMLDivElement | null>(null);

  return (
    <section className="flex flex-col gap-2 mt-60">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1">
          <FontAwesomeIcon icon={faChartSimple} className="text-primary text-[12px]" />
          <span className="text-primary/50 text-[12px]">|</span>
          <span className="text-primary font-semibold text-[12px]">Monetização Inteligente</span>
        </div>
        <h1 className="text-4xl font-bold max-w-2xl">Transforme seu servidor em uma fonte de receita</h1>
        <div className="flex flex-col gap-1">
          <p className="text-foreground/70 text-sm max-w-2xl">
            O Amethys Pro integra soluções de pagamento direto no Discord, permitindo que você monetize sua comunidade sem depender de plataformas externas. <span className="font-semibold text-foreground">Ofereça assinaturas, produtos digitais ou serviços com transações rápidas, seguras e diversificadas.</span>
          </p>
          <Link
            href="/pricing"
            className="text-foreground flex items-center gap-1 w-fit px-4 py-1 bg-foreground/2 border border-foreground/10 rounded-lg hover:bg-foreground/10 duration-100 transition-all cursor-pointer my-2"
          >
            <span className="text-[12px] text-foreground/80">Explore nossos produtos</span>
            <FontAwesomeIcon icon={faChevronRight} className="text-foreground/70 text-[12px]" />
          </Link>
        </div>
      </div>

      <section ref={estimativaRef as any} className="flex flex-col gap-2">
        <span className="text-[12px] text-primary">Estimativa de resultados com a Amethys</span>
        <div className="flex flex-col lg:flex-row gap-2 md:gap-5">
          <div className="w-full" ref={chartRef}>
            <CustomLineChart data={CHART_DATA} className="outline-none" />
          </div>
          <div className="w-full min-w-full lg:min-w-0 md:max-w-[300px] self-start">
            <p className="text-foreground/70 text-sm">
              Veja como sua loja pode evoluir com o apoio das nossas soluções digitais. <span className="font-semibold text-foreground">Resultados reais, pensados para o seu crescimento.</span>
            </p>
            <hr className="border-foreground/10 my-2" />
            <span className="text-primary text-[12px] flex items-center gap-1">
              <Tooltip
                content="Os valores apresentados são estimativas e podem variar conforme o segmento e o investimento inicial."
                className="max-w-xs p-2 bg-background border border-foreground/10 text-foreground/70 text-[12px]"
                delay={0}
                closeDelay={0}
                showArrow
              >
                Estimativa para os primeiros 2 meses
              </Tooltip>
            </span>
            <p className="text-foreground/70 flex items-center gap-1">
              <span className="font-semibold text-foreground">R$ 50,00</span>
              <span className="text-sm">investimento inicial</span>
            </p>
            <p className="text-foreground/70 flex items-center gap-1">
              <span className="font-semibold text-foreground">R$ 2.500,00</span>
              <span className="text-sm">lucro líquido estimado</span>
            </p>
          </div>
        </div>
      </section>
    </section>
  );
}


