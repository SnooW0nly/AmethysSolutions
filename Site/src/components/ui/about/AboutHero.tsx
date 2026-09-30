"use client";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCreditCard } from "@fortawesome/free-regular-svg-icons";
import { faPix } from "@fortawesome/free-brands-svg-icons";
import { faUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { Button } from "@heroui/react";

type Venda = { valor: number; data: string; metodo: "pix" | "cartao" };

function formatarValor(valor: number) {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function AboutHero() {
  const vendas: Venda[] = [
    { valor: 100, data: "50s atrás", metodo: "pix" },
    { valor: 100, data: "1h atrás", metodo: "pix" },
    { valor: 50, data: "2h atrás", metodo: "cartao" },
    { valor: 20, data: "3h atrás", metodo: "pix" },
    { valor: 100, data: "3h atrás", metodo: "cartao" },
  ];

  return (
    <section className="relative w-full flex flex-col items-center justify-center gap-12 md:px-28 md:py-15 overflow-hidden rounded-xl">
      {/* Fundo radial + blur */}
      <div className="hidden md:block absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(var(--primary-rgb),0.06)_0%,rgba(0,0,0,0)_70%)] pointer-events-none" />
      <div className="hidden md:block absolute inset-0 backdrop-blur-[120px] bg-[rgba(20,20,20,0.25)]" />

      <div className="gap-12 flex flex-col justify-between w-full md:flex-row">
        {/* Texto */}
        <div className="relative z-10 flex flex-col max-w-lg text-left">
          <h1 className="text-5xl font-bold tracking-tight text-foreground mb-3">
            Automatize, venda e cresça
          </h1>
          <p className="text-foreground/60 text-sm md:text-base leading-relaxed mb-5">
            Transforme seu Discord em uma máquina de vendas. Mais tempo para
            você, mais vendas para o seu negócio.
          </p>

          <p className="text-foreground/70 text-sm leading-relaxed mb-3">
            Com a{" "}
            <span className="font-semibold text-primary">Amethys</span>, vender no
            Discord é tão simples que você pode faturar enquanto joga, assiste sua
            série favorita ou aproveita o intervalo do café.
          </p>
          <p className="text-foreground/70 text-sm leading-relaxed mb-6">
            Nós cuidamos de tudo:{" "}
            <span className="font-semibold text-primary">
              pagamentos, suporte, segurança e automação
            </span>
            . Assim, você pode focar no que realmente importa:{" "}
            <span className="font-semibold text-primary">
              criar, expandir e lucrar.
            </span>
          </p>

          <div className="flex flex-row gap-3">
          <Button
              className="bg-primary text-foreground hover:bg-primary/90 transition-colors text-sm"
              onClick={() => (window.location.href = "/pricing")}
            >
              Começar agora
            </Button>
            <Button
              className="bg-transparent border border-foreground/10 text-foreground hover:bg-foreground/[0.05] transition-colors text-sm"
              onClick={() => (window.location.href = "/dashboard")}
            >
              <span className="flex items-center gap-1">
                Acessar Dashboard
                <FontAwesomeIcon icon={faUpRightFromSquare} className="text-[11px]" />
              </span>
            </Button>
          </div>
        </div>

        {/* Card de vendas */}
        <div className="relative flex flex-col justify-between z-10 w-full max-w-sm rounded-2xl border border-white/5 bg-white/[0.03] shadow-[0_0_40px_-10px_rgba(0,0,0,0.4)] p-5 backdrop-blur-xl">
          <p className="text-xs uppercase tracking-widest text-foreground/40 font-semibold mb-2">
            Últimas vendas
          </p>
          <div className="flex flex-col gap-2">
            {vendas.map((venda, index) => (
              <div
                key={index}
                className="flex items-center gap-3 border border-white/[0.06] bg-white/[0.04] hover:bg-white/[0.07] transition-colors rounded-xl px-3 py-2"
              >
                <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 border border-primary/20">
                  <FontAwesomeIcon
                    icon={venda.metodo === "pix" ? faPix : faCreditCard}
                    className="text-primary text-sm"
                  />
                </div>
                <div className="flex flex-col flex-1">
                  <div className="flex justify-between text-xs text-foreground/60">
                    <span>Venda concluída</span>
                    <span>{venda.data}</span>
                  </div>
                  <p className="text-sm text-foreground/80 font-medium">
                    {formatarValor(venda.valor)}{" "}
                    <span className="text-foreground/50 font-normal">
                      disponíveis
                    </span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
