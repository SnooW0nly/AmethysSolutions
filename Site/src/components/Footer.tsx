"use client";

import { Link } from "@heroui/link";
import { footer } from "@/config/footer";
import Image from "next/image";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faExternalLink } from "@fortawesome/free-solid-svg-icons";
import { faDiscord, faGithub, faYoutube } from "@fortawesome/free-brands-svg-icons";
import { siteConfig } from "@/config/site";

const legalLinks = [
  { label: "Termos de Serviço", href: "/terms" },
  { label: "Política de Privacidade", href: "/terms/legais/privacy" },
  { label: "Política de Cookies", href: "/terms/legais/cookies" },
  { label: "Política de Reembolso", href: "/terms/legais/reembolso" },
  { label: "DPA", href: "/terms/legais/dpa" },
  { label: "AUP", href: "/terms/legais/aup" },
];

export const Footer = () => (
  <footer className="relative flex flex-col border-t border-foreground/10 w-full">

    {/* Conteúdo principal */}
    <section className="relative z-10 flex w-full flex-col md:flex-row gap-6 md:gap-16 max-w-7xl mx-auto px-6 pt-10 md:justify-between">

      {/* Logo + info + redes */}
      <div className="flex flex-col gap-2 shrink-0">
        <Link href="/" className="flex flex-row gap-2 items-center select-none w-fit">
          <Image src="/amethys.png" alt="Logo" height={40} width={40} />
          <div className="flex flex-col leading-tight">
            <span className="text-foreground/90 font-normal font-sans text-[13px]">Amethys</span>
            <span className="text-foreground/60 font-normal font-sans text-[13px]">Solutions</span>
          </div>
        </Link>
        <div className="flex flex-col">
          <p className="text-foreground/60 text-[12px]">© 2025 Todos os direitos reservados</p>
          <p className="text-foreground/60 text-[12px]">CNPJ: {siteConfig.cnpj}</p>
        </div>
        <div className="flex flex-row gap-2">
          <Link href="/socials/discord" className="flex items-center select-none w-fit">
            <FontAwesomeIcon icon={faDiscord} className="text-[18px] text-foreground/70 hover:text-foreground transition-colors" />
          </Link>
          <Link href="/socials/github" className="flex items-center select-none w-fit">
            <FontAwesomeIcon icon={faGithub} className="text-[18px] text-foreground/70 hover:text-foreground transition-colors" />
          </Link>
          <Link href="/socials/youtube" className="flex items-center select-none w-fit">
            <FontAwesomeIcon icon={faYoutube} className="text-[18px] text-foreground/70 hover:text-foreground transition-colors" />
          </Link>
        </div>
      </div>

      <hr className="border-foreground/10 md:hidden" />

      {/* Links das categorias */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-x-10 gap-y-6 flex-1">
        {footer.map((category, categoryIdx) => (
          <div key={categoryIdx} className="flex flex-col gap-2">
            <span className="text-foreground/50 text-[11px] uppercase tracking-wider">{category.category}</span>
            <div className="flex flex-col gap-1">
              {category.links.map((link, linkIdx) => (
                <Link
                  key={linkIdx}
                  href={link.href}
                  isExternal={link.external}
                  className="text-foreground/75 hover:text-foreground text-[13px] flex flex-row gap-1 items-center transition-colors"
                >
                  {link.label}
                  {link.external && <FontAwesomeIcon icon={faExternalLink} className="text-[9px]" />}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>

    </section>

    {/* Separador + links legais */}
    <div className="relative z-10 max-w-7xl mx-auto px-6 w-full mt-8">
      <hr className="border-foreground/10 mb-4" />
      <div className="flex flex-wrap gap-x-4 gap-y-2 pb-6">
        <span className="text-foreground/40 text-[11px] uppercase tracking-wider self-center mr-1">Legal</span>
        {legalLinks.map((link, idx) => (
          <Link
            key={idx}
            href={link.href}
            className="text-foreground/55 hover:text-foreground text-[12px] transition-colors"
          >
            {link.label}
          </Link>
        ))}
      </div>
    </div>

    {/* Marca d'água — overflow-hidden só no wrapper dela */}
    <div className="overflow-hidden w-full pointer-events-none select-none z-0">
      <p className="text-center text-[22vw] font-black text-foreground opacity-5 leading-none tracking-tighter -mb-[6vw]">
        Amethys
      </p>
    </div>

  </footer>
);