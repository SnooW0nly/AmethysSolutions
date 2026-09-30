import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faShield, faChevronRight, faStar, faLock, faArrowLeft, faArrowRight, faPlus, faMinus, faLayerGroup, faArrowUp, faCaretUp } from "@fortawesome/free-solid-svg-icons";
import { Link } from "@heroui/react";
import { faGoogle, faOpenai } from "@fortawesome/free-brands-svg-icons";
import React from "react";

type CoreProps = {
  className?: string;
};

function Core({ className }: CoreProps) {
  return (
    <div
      className={[
        "relative aspect-square w-40 select-none",
        "bg-[linear-gradient(180deg,#0f1216_0%,#0c1014_45%,#0a0d11_100%)]",
        "border border-white/10",
        "shadow-[0_0_0_1px_rgba(255,255,255,0.03),0_10px_30px_rgba(0,0,0,0.35)]",
        className || "",
      ].join(" ")}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-1/2 bg-gradient-to-b from-white/5 to-transparent" />

      <div className="absolute right-3 top-3 opacity-70">
        <img
            src="https://www.vectorlogo.zone/logos/mongodb/mongodb-icon.svg"
            alt="MongoDB"
            className="w-6 h-6 filter grayscale brightness-75"
        />
      </div>

      <div className="absolute left-3 bottom-1.5">
        <span className="font-[monospace] uppercase text-xs text-white/30">
          MongoDB
        </span>
      </div>
    </div>
  );
}

export function InfraestruturaSection() {
  return (
    <section className="mt-40 md:mt-50 flex flex-row justify-between w-full">
        <div className="w-full lg:w-1/2 flex flex-col gap-2">
            <div className="flex items-center gap-1">
            <FontAwesomeIcon icon={faLayerGroup} className="text-primary text-[12px]" />
            <span className="text-primary/50 text-[12px]">|</span>
            <span className="text-primary font-semibold text-[12px]">Estrutura empresarial</span>
            </div>
            <h1 className="text-4xl font-bold">
            Infraestrutura robusta, feita para escalar com segurança
            </h1>
            <div className="flex flex-col gap-1">
            <p className="text-foreground/70 text-sm max-w-xl">
                Nossa plataforma combina desempenho, confiabilidade e segurança de nível corporativo para sustentar aplicações modernas e em constante crescimento.
            </p>
            <Link
                href="/pricing"
                className="text-foreground flex items-center gap-1 w-fit px-4 py-1 bg-foreground/2 border border-foreground/10 rounded-lg hover:bg-foreground/10 duration-100 transition-all cursor-pointer my-2"
            >
                <span className="text-[12px] text-foreground/80">Explore nossos produtos</span>
                <FontAwesomeIcon icon={faChevronRight} className="text-foreground/70 text-[12px]" />
            </Link>
            </div>
            <hr className="border-foreground/10 my-4" />

            <div className="flex flex-col gap-15 mt-2">
                <div className="flex flex-row gap-4 justify-between">
                    <p className="text-foreground/90 text-sm font-semibold">Criptografia de ponta</p>
                    <p className="text-foreground/60 text-xs leading-tight md:max-w-xs max-w-1/2">
                    Proteja informações sensíveis com padrões avançados de criptografia, garantindo sigilo e integridade em cada transação e comunicação.
                    </p>
                </div>

                <div className="flex flex-row gap-4 justify-between">
                    <p className="text-foreground/90 text-sm font-semibold">
                    <a href="https://starckr.app" target="_blank">
                        Hospedagem qualificada <FontAwesomeIcon icon={faArrowUp} className="text-foreground/70 text-[12px] rotate-50" />
                    </a>
                    </p>
                    <p className="text-foreground/60 text-xs leading-tight md:max-w-xs max-w-1/2">
                    Servidores dedicados com IPs exclusivos e operação 24/7, garantindo desempenho estável e alta disponibilidade.
                    </p>
                </div>

                <div className="flex flex-row gap-4 justify-between">
                    <p className="text-foreground/90 text-sm font-semibold">Monitoramento em tempo real</p>
                    <p className="text-foreground/60 text-xs leading-tight md:max-w-xs max-w-1/2">
                    Acompanhe métricas essenciais e receba alertas instantâneos para manter a operação segura e proativa, minimizando riscos e falhas.
                    </p>
                </div>

                <div className="flex flex-row gap-4 justify-between">
                    <p className="text-foreground/90 text-sm font-semibold">Sistema de análises</p>
                    <p className="text-foreground/60 text-xs leading-tight md:max-w-xs max-w-1/2">
                    Obtenha relatórios detalhados e insights estratégicos que auxiliam na tomada de decisões, otimização de recursos e crescimento sustentável.
                    </p>
                </div>
            </div>
        </div>
        <div className="w-3/7 h-auto rounded-lg p-7 border border-dashed border-foreground/10 lg:block hidden">
           <div className="flex flex-col">
                <p className="text-foreground/60 uppercase text-xs font-[monospace]">Sua aplicação</p>
                <p className="text-foreground/60 text-xs leading-tight md:max-w-sm">
                Por trás de uma interface intuitiva existe uma infraestrutura sólida que integra servidores, dashboards e bots com alta performance e confiabilidade empresarial.
                </p>
            </div>

            <div className="mt-5 flex flex-row gap-4">
                <div className="h-auto w-[1px] border-l border-dashed border-foreground/10" />

                <div>
                {/* BANCO DE DADOS */}
                <div className="flex flex-col gap-2">
                    <p className="text-foreground/60 uppercase text-xs font-[monospace]">Banco de dados</p>
                    <div className="flex flex-row gap-3">
                    <Core />
                    <div className="flex flex-col gap-2 justify-between">
                        <p className="text-foreground/60 text-xs leading-tight mr-2 md:max-w-2xs">
                        Dados críticos armazenados com segurança e escalabilidade, garantindo consistência e velocidade para toda a sua aplicação.
                        </p>
                        <div className="h-[60%] w-full rounded-md bg-[repeating-linear-gradient(45deg,rgba(255,255,255,0.10)_0,rgba(255,255,255,0.10)_1,transparent_1px,transparent_8px)]" />
                    </div>
                    </div>
                </div>

                {/* AGENTES DE IA */}
                <div className="flex flex-col gap-2 mt-6">
                    <p className="text-foreground/60 uppercase text-xs font-[monospace]">Agentes de IA</p>
                    <div className="p-3 border border-foreground/10 w-full justify-center items-center">
                        <div className="flex flex-row gap-2 items-center">
                            <svg viewBox="0 0 128 128" className="w-20 h-20">
                                <g className="text-foreground/20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                                    <ellipse cx="64" cy="64" rx="24" ry="50" />
                                    <ellipse cx="64" cy="64" rx="24" ry="50" transform="rotate(60 64 64)" />
                                    <ellipse cx="64" cy="64" rx="24" ry="50" transform="rotate(-60 64 64)" />
                                </g>

                                <circle cx="64" cy="64" r="10" className="text-foreground/20" fill="currentColor" />
                            </svg>
                            <div className="flex flex-col">
                                <p className="text-foreground/70 text-[10px] uppercase font-[monospace]">Amethys AI</p>
                                <p className="text-foreground/70 text-[11px] leading-tight md:max-w-xs">
                                Tecnologia de processamento de linguagem natural para respostas precisas, automações inteligentes e análise contextual em tempo real.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* HOSPEDAGEM */}
                <div className="flex flex-col gap-1 mt-6">
                    <p className="text-foreground/60 uppercase text-xs font-[monospace]">Hospedagem</p>
                    <div className="flex flex-rol gap-4">
                    <div className="w-fit mt-1">
                        <div className="flex flex-row justify-between">
                        <div className="border-t border-l border-foreground/10 w-3 h-3" />
                        <div className="border-t border-r border-foreground/10 w-3 h-3" />
                        </div>
                        <img src="amd-epic.png" className="h-35 w-25 object-cover filter grayscale brightness-60 mx-3" />
                        <div className="flex flex-row justify-between">
                        <div className="border-b border-l border-foreground/10 w-3 h-3" />
                        <div className="border-b border-r border-foreground/10 w-3 h-3" />
                        </div>
                    </div>
                    <div className="flex flex-col justify-center">
                        <p className="text-foreground/60 text-[12px] font-[monospace] uppercase">AMD Epyc™</p>
                        <p className="text-foreground/60 text-xs leading-tight mr-2 max-w-[200px] xl:max-w-2xs">
                        Servidores com alta capacidade de processamento e estabilidade para suportar aplicações grandes, fornecendo alta performance e escalabilidade para seus serviços.
                        </p>
                        <div className="flex flex-row mt-4">
                        {Array.from({ length: 5 }).map((_, i) => (
                            <FontAwesomeIcon key={i} icon={faStar} className="text-foreground/50 text-[11px]" />
                        ))}
                        <div className="ml-2 h-[1px] w-full border-b border-foreground/10 self-center" />
                        </div>
                        <div className="flex flex-row gap-2 mt-1">
                        <img src="amethys.png" className="h-8 w-8 filter grayscale brightness-110" />
                        <div className="h-[70%] self-center w-[1px] border-l border-foreground/10" />
                        <a href="https://starckr.app" target="_blank"><img src="starckr.png" className="h-8 w-8 filter grayscale brightness-60" /></a>
                        </div>
                    </div>
                    </div>
                </div>
                </div>
            </div>
        </div>
    </section>
  )
}