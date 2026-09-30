"use client";

/**
 * src/app/dashboard/admin/sections/services/ServicesSection.tsx
 *
 * Hub de serviços do admin — Members ativo, demais bloqueados (em breve).
 * Clicking em Members navega para /dashboard/admin/services/members
 */

import { useRouter } from "next/navigation";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faUsers,
  faBolt,
  faCoins,
  faGamepad,
  faLock,
  faArrowRight,
  faCheckCircle,
} from "@fortawesome/free-solid-svg-icons";
import { motion } from "framer-motion";

interface ServiceDef {
  id: string;
  label: string;
  description: string;
  icon: any;
  active: boolean;
  href?: string;
  badge?: string;
  stats?: string;
}

const SERVICES: ServiceDef[] = [
  {
    id: "members",
    label: "Members",
    description: "Gerencie serviços de membros Discord — online e offline. Configure preços, IDs de serviço na Revision e monitore todos os pedidos.",
    icon: faUsers,
    active: true,
    href: "/dashboard/admin/services/members",
    badge: "Ativo",
    stats: "RevisionSMM",
  },
  {
    id: "boost",
    label: "Boost",
    description: "Impulsionamentos de servidor Discord. Em breve você poderá configurar preços, quantidades e integrações de boost.",
    icon: faBolt,
    active: false,
    badge: "Em breve",
  },
  {
    id: "robux",
    label: "Robux",
    description: "Venda de Robux para Roblox. Integração com provedores externos em desenvolvimento.",
    icon: faCoins,
    active: false,
    badge: "Em breve",
  },
  {
    id: "outros",
    label: "Outros Serviços",
    description: "Novos serviços serão adicionados conforme a plataforma cresce. Fique ligado!",
    icon: faGamepad,
    active: false,
    badge: "Planejado",
  },
];

export function ServicesSection() {
  const router = useRouter();

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-black mb-1">Serviços</h2>
        <p className="text-foreground/50 text-sm">
          Gerencie os serviços disponíveis na plataforma. Clique em um serviço ativo para acessar sua configuração.
        </p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SERVICES.map((svc, i) => (
          <motion.div
            key={svc.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: i * 0.07 }}
          >
            {svc.active ? (
              /* Active card — clickable */
              <button
                onClick={() => svc.href && router.push(svc.href)}
                className="group w-full text-left relative rounded-2xl border-2 border-primary/30 bg-primary/[0.04] hover:border-primary/60 hover:bg-primary/[0.07] transition-all duration-200 p-6 flex flex-col gap-4 overflow-hidden"
              >
                {/* Glow */}
                <div className="absolute inset-0 pointer-events-none bg-primary/5 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity" />

                <div className="flex items-start justify-between relative z-10">
                  <div className="w-12 h-12 rounded-xl bg-primary/15 border border-primary/25 flex items-center justify-center text-primary text-xl">
                    <FontAwesomeIcon icon={svc.icon} />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/25 text-emerald-400">
                      <FontAwesomeIcon icon={faCheckCircle} className="text-[9px]" />
                      {svc.badge}
                    </span>
                  </div>
                </div>

                <div className="relative z-10">
                  <h3 className="font-black text-lg mb-1">{svc.label}</h3>
                  <p className="text-sm text-foreground/55 leading-relaxed">{svc.description}</p>
                </div>

                <div className="relative z-10 flex items-center justify-between mt-auto pt-2 border-t border-primary/15">
                  <span className="text-xs text-foreground/40 font-mono">{svc.stats}</span>
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-primary group-hover:gap-2.5 transition-all">
                    Acessar
                    <FontAwesomeIcon icon={faArrowRight} className="text-[11px]" />
                  </span>
                </div>
              </button>
            ) : (
              /* Locked card */
              <div className="relative rounded-2xl border border-foreground/8 bg-foreground/[0.02] p-6 flex flex-col gap-4 overflow-hidden opacity-60 cursor-not-allowed select-none">
                {/* Lock overlay */}
                <div className="absolute top-3 right-3">
                  <FontAwesomeIcon icon={faLock} className="text-foreground/20 text-xs" />
                </div>

                <div className="w-12 h-12 rounded-xl bg-foreground/8 border border-foreground/10 flex items-center justify-center text-foreground/30 text-xl">
                  <FontAwesomeIcon icon={svc.icon} />
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-black text-lg">{svc.label}</h3>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-foreground/8 border border-foreground/12 text-foreground/35">
                      {svc.badge}
                    </span>
                  </div>
                  <p className="text-sm text-foreground/40 leading-relaxed">{svc.description}</p>
                </div>

                <div className="pt-2 border-t border-foreground/8">
                  <span className="text-xs text-foreground/25">Indisponível no momento</span>
                </div>
              </div>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}