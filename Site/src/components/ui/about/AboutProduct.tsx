"use client";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { Link } from "@heroui/react";
import { featuresAbout } from "@/config/features";


export function AboutProduct() {
  return (
    <section>
      <div className="flex flex-col gap-2 mt-20">
        <h2 className="text-2xl font-bold">Conheça o nosso produto</h2>
        <p className="text-foreground/70 text-sm leading-relaxed">
          <span className="font-bold text-foreground/90">Feito para você.</span> Na Amethys,
          projetamos o bot mais completo para automatizar de vez a sua loja no Discord.
          Nosso foco é simples: <span className="font-bold text-primary">velocidade, segurança e praticidade</span>.
          <br />
          Receba pagamentos em múltiplos métodos, gerencie pedidos com facilidade, ofereça suporte
          instantâneo e mantenha sua comunidade protegida. <span className="font-bold text-foreground/90">Tudo em um só lugar.</span>
          <br />
          Aqui, tecnologia e experiência andam juntas para impulsionar o seu negócio.
        </p>
        <div className="flex flex-row gap-3">
          <Link
            href="/tutorials"
            className="text-foreground text-sm flex items-center gap-1 w-fit px-4 py-2 bg-foreground/2 border border-foreground/10 rounded-lg hover:bg-foreground/10 duration-100 transition-all"
          >
            Veja como funciona <FontAwesomeIcon icon={faUpRightFromSquare} className="text-[11px]" />
          </Link>
          <Link
            href="/pricing"
            className="text-foreground text-sm flex items-center gap-1 w-fit px-4 py-2 bg-foreground/2 border border-foreground/10 rounded-lg hover:bg-foreground/10 duration-100 transition-all"
          >
            Conheça nossos planos <FontAwesomeIcon icon={faUpRightFromSquare} className="text-[11px]" />
          </Link>
        </div>
        <div className="my-1" />
      </div>

      <div className="flex flex-col md:flex-row gap-2 w-full">
        {/* Feedbacks reais no lugar do vídeo */}
        <div className="w-full md:w-1/2 rounded-2xl overflow-hidden border border-white/5 bg-white/[0.03] shadow-[0_0_40px_-10px_rgba(0,0,0,0.4)]" style={{ aspectRatio: "16/9" }}>
          <iframe
            src="https://www.youtube.com/embed/VNzwiu1MICs?si=aURU5fLo1epbb0ty"
            title="Amethys — apresentação"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
            className="w-full h-full"
          />
        </div>

        {/* Features list — mantido igual */}
        <div className="flex flex-col gap-1 w-full md:w-1/2 bg-foreground/3 border border-foreground/5 rounded-xl p-4">
          {featuresAbout.map((feature, index) => (
            <div key={index} className="flex flex-col gap-1 items-start">
              <div className="flex flex-row gap-1 items-center">
                <FontAwesomeIcon icon={feature.icon} className="text-[12px]" />
                <span className="text-[0.875rem]">{feature.title}</span>
              </div>
              <p className="text-foreground/70 font-[370] text-[13px] leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
