"use client";

import { Link } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChevronRight, faLeaf, faMedal, faShield } from "@fortawesome/free-solid-svg-icons";
import { featuresAbout, featuresCards } from "@/config/features";
import { ReactNode } from "react";


type FeatureCardProps = {
  icon: ReactNode;
  title: string;
  description: string;
  className?: string;
  hideOnMobile?: boolean;
};

function FeatureCard({ icon, title, description, className = "", hideOnMobile = false }: FeatureCardProps) {
  return (
    <div className={`flex flex-col justify-center p-5 border border-foreground/5 rounded-xl ${className} ${hideOnMobile ? "hidden md:flex" : ""}`}>
      <div className="flex flex-col gap-2">
        {icon}
        <p className="text-md">{title}</p>
      </div>
      <p className="text-foreground/70 text-sm">
        {description}
      </p>
    </div>
  );
}

type FeatureCardFeatureProps = {
  icon: ReactNode;
  title: string;
  description: string;
  chip: string;
};

function FeatureCardFeature({ icon, title, description, chip }: FeatureCardFeatureProps) {
  return (
    <div className="flex flex-row items-center justify-between gap-4 py-1.5">
      <div className="flex flex-row items-center gap-4">
        <div className="flex flex-col">
          <p className="text-sm">{title}</p>
          <p className="text-foreground/70 text-xs">{description}</p>
        </div>
      </div>
      <span className="text-primary text-xs px-2 py-1 bg-foreground/2 border border-foreground/5 rounded-md">{chip}</span>
    </div>
  );
}

export function PersonalizacaoSegurancaSection() {
  return (
    <section className="mt-30 md:mt-40">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1">
          <FontAwesomeIcon icon={faShield} className="text-primary text-[12px]" />
          <span className="text-primary/50 text-[12px]">|</span>
          <span className="text-primary font-semibold text-[12px]">Personalização e Segurança</span>
        </div>
        <h1 className="text-4xl font-bold max-w-2xl">Mantenha seus clientes satisfeitos e protegidos</h1>
        <div className="flex flex-col gap-1">
          <p className="text-foreground/70 text-sm max-w-2xl">
            Oferecemos liberdade total para personalizar experiências e recursos de acordo com sua comunidade. Ao mesmo tempo, protegemos seu servidor com sistemas robustos de segurança, <span className="font-semibold text-foreground">garantindo estabilidade em cada ação.</span>
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
      <section className="flex flex-col md:flex-col lg:flex-row gap-2 w-full mt-2">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 lg:max-w-2xl">
          {featuresCards.map((feature, index) => (
            <FeatureCard
              key={index}
              icon={<FontAwesomeIcon icon={feature.icon} className="text-primary text-2xl" />}
              title={feature.title}
              description={feature.description}
              hideOnMobile={feature.hideOnMobile}
            />
          ))}
        </div>
        <div className="flex flex-col gap-2">
          <div className="md:w-full h-full">
            <div className="p-5 bg-background border border-foreground/5 rounded-xl h-full">
              <div className="flex flex-col gap-2">
                <FontAwesomeIcon icon={faLeaf} className="text-primary text-2xl" />
                <p className="text-md mt-1 font-semibold">Segurança inteligente para o seu servidor</p>
              </div>
              <p className="text-foreground/70 text-sm">
                Com soluções avançadas de proteção e automação, seu servidor permanece seguro contra ataques,
                fraudes e uso indevido. Otimize a gestão da sua comunidade com mais eficiência e confiança.
              </p>
              <hr className="mt-3 my-1.5 border-foreground/5" />
              <div className="flex flex-col gap-1">
                {FeatureCardFeature({
                  icon: <FontAwesomeIcon icon={faShield} className="text-primary text-lg" />,
                  title: "Controle de acesso",
                  description: "Gerencie quem usa seus recursos e bloqueie atividades indesejadas",
                  chip: "Bloqueio"
                })}
                {FeatureCardFeature({
                  icon: <FontAwesomeIcon icon={faShield} className="text-primary text-lg" />,
                  title: "Prevenção de fraudes",
                  description: "Identifique atividades suspeitas e minimize prejuízos com pagamentos",
                  chip: "Fraude"
                })}
                {FeatureCardFeature({
                  icon: <FontAwesomeIcon icon={faShield} className="text-primary text-lg" />,
                  title: "Moderação automatizada",
                  description: "Proteja sua comunidade com sistemas de moderação com IA",
                  chip: "Proteção"
                })}
                {FeatureCardFeature({
                  icon: <FontAwesomeIcon icon={faShield} className="text-primary text-lg" />,
                  title: "Insights e análises",
                  description: "Monitore o desempenho do servidor com relatórios detalhados",
                  chip: "Análises"
                })}
              </div>
            </div>
          </div>
        </div>
      </section>
    </section>
  );
}


