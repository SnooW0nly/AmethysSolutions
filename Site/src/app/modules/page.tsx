"use client";

import { useRef } from "react";
import dynamic from "next/dynamic";
import { motion, useScroll, useTransform } from "framer-motion";
import { Button, Link } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faRobot,
  faGift,
  faStore,
  faEnvelope,
  faShield,
  faChartLine,
  faGear,
  faTicket,
  faCoins,
  faChevronRight,
  faBolt,
  faStar,
  faArrowRight,
  faCircleCheck,
  faLayerGroup,
  faCloud,
  faPaintBrush,
} from "@fortawesome/free-solid-svg-icons";
import { faDiscord } from "@fortawesome/free-brands-svg-icons";
import GridLines from "@/components/GridLines";

// ── Dynamic import keeps Three.js client-only (no SSR) ──────────────────────
const Notebook3D = dynamic(
  () => import("@/components/Notebook3D").then((m) => ({ default: m.Notebook3D })),
  { ssr: false, loading: () => <NotebookSkeleton /> }
);

// ── Skeleton shown while notebook loads ──────────────────────────────────────
function NotebookSkeleton() {
  return (
    <div className="w-full flex items-center justify-center" style={{ height: 700 }}>
      <div className="flex flex-col items-center gap-3 opacity-30">
        <div className="w-40 h-52 rounded-lg border border-foreground/10 bg-foreground/[0.03] animate-pulse" />
        <span className="text-[11px] text-foreground/40 font-mono">carregando caderno...</span>
      </div>
    </div>
  );
}

// ── Types ────────────────────────────────────────────────────────────────────
type Module = {
  id: string;
  icon: any;
  badge: string;
  title: string;
  description: string;
  features: string[];
  color: string;
};

// ── Data ─────────────────────────────────────────────────────────────────────
const modules: Module[] = [
  {
    id: "automations",
    icon: faBolt,
    badge: "Automações",
    title: "Automações",
    description:
      "O coração proativo do bot. Configure boas-vindas, moderação assistida por IA, mensagens automáticas, rastreamento de convites e muito mais — tudo num único painel.",
    features: ["AmethysAI Chat & Moderador", "Boas-vindas personalizadas", "Invite Tracker", "Mensagens & reações automáticas"],
    color: "from-violet-500/20 to-transparent",
  },
  {
    id: "cloud",
    icon: faCloud,
    badge: "Cloud",
    title: "Cloud",
    description:
      "Integração com serviços externos via WebSocket e API. Gerencie gifts, tarefas assíncronas e credenciais de nuvem com comunicação em tempo real.",
    features: ["Criação e gestão de gifts", "Tarefas assíncronas", "Integração via WebSocket", "Gerenciamento de credenciais"],
    color: "from-sky-500/20 to-transparent",
  },
  {
    id: "customization",
    icon: faPaintBrush,
    badge: "Customização",
    title: "Customização",
    description:
      "Adapte o bot à identidade visual do seu servidor. Edite status, avatar, cores primárias e alterne entre modo embed e componentes interativos.",
    features: ["Status e atividade do bot", "Nome e avatar", "Cores primárias", "Modo embed ou components"],
    color: "from-pink-500/20 to-transparent",
  },
  {
    id: "giveaways",
    icon: faGift,
    badge: "Sorteios",
    title: "Sorteios",
    description:
      "Sistema completo para criar, configurar e executar sorteios com requisitos avançados, tarefas de participação, cargos bônus e rolagem automática de vencedores.",
    features: ["Criação e edição de sorteios", "Requisitos e cargos bônus", "Tarefas de participação", "Rolagem automática"],
    color: "from-amber-500/20 to-transparent",
  },
  {
    id: "loja",
    icon: faStore,
    badge: "Loja",
    title: "Loja",
    description:
      "Ecossistema de e-commerce completo dentro do Discord. Gerencie produtos, clientes, saldo interno, cashback e personalize cada detalhe da sua vitrine.",
    features: ["Gerenciar produtos", "Sistema de saldo & cashback", "Personalização da loja", "Gestão de clientes"],
    color: "from-emerald-500/20 to-transparent",
  },
  {
    id: "messages",
    icon: faEnvelope,
    badge: "Mensagens",
    title: "Mensagens",
    description:
      "Módulo auxiliar de templates que garante consistência em todas as comunicações do bot — embeds, textos simples e interações com componentes.",
    features: ["Templates reutilizáveis", "Embeds formatados", "Padronização visual", "Integração com outros módulos"],
    color: "from-blue-500/20 to-transparent",
  },
  {
    id: "protection",
    icon: faShield,
    badge: "Proteção",
    title: "Proteção",
    description:
      "Camada de segurança dedicada ao servidor. Configure proteções contra spam, flood e menções em massa, além de regras de privatização de canais.",
    features: ["Anti-spam & flood", "Proteção geral configurável", "Privatização de canais", "Controle granular de acesso"],
    color: "from-red-500/20 to-transparent",
  },
  {
    id: "rendimentos",
    icon: faChartLine,
    badge: "Rendimentos",
    title: "Rendimentos",
    description:
      "Painel financeiro com estatísticas de vendas, receita mensal, top produtos, geração de gráficos e exportação de dados para análise estratégica.",
    features: ["Stats gerais e mensais", "Top produtos", "Filtros e gráficos", "Exportação de dados"],
    color: "from-teal-500/20 to-transparent",
  },
  {
    id: "settings",
    icon: faGear,
    badge: "Configurações",
    title: "Configurações",
    description:
      "Painel central de controle para gerenciar cargos, canais, formas de pagamento, anti-fake, permissões e extensões do bot em um único lugar.",
    features: ["Cargos & canais", "Formas de pagamento", "Anti-fake", "Permissões & extensões"],
    color: "from-orange-500/20 to-transparent",
  },
  {
    id: "tickets",
    icon: faTicket,
    badge: "Tickets",
    title: "Tickets",
    description:
      "Sistema robusto de suporte com painéis interativos, cargos de atendimento, horários, transcrições automáticas e integração com IA para triagem.",
    features: ["Criação e fechamento", "Atribuição & prioridade", "Transcrições automáticas", "Integração com IA"],
    color: "from-indigo-500/20 to-transparent",
  },
  {
    id: "economia",
    icon: faCoins,
    badge: "Economia",
    title: "Economia",
    description:
      "Moeda virtual completa com daily/weekly, trabalho, pesca, mineração, banco, slots, loja de itens, casamento e ranking — tudo configurável.",
    features: ["Recompensas diárias", "Mini-jogos & comércio", "Banco e inventário", "Interações sociais"],
    color: "from-yellow-500/20 to-transparent",
  },
];

// ── Stat strip ────────────────────────────────────────────────────────────────
function StatStrip() {
  const stats = [
    { value: "11", label: "Módulos disponíveis" },
    { value: "60+", label: "Sub-funcionalidades" },
    { value: "1", label: "Painel unificado" },
    { value: "∞", label: "Possibilidades" },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mt-16">
      {stats.map((s, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, scale: 0.92 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: i * 0.08 }}
          className="flex flex-col items-center gap-1 py-5 px-4 rounded-xl border border-foreground/8 bg-foreground/[0.02] text-center"
        >
          <span className="text-3xl md:text-4xl font-black text-foreground tabular-nums">{s.value}</span>
          <span className="text-foreground/40 text-[11px] leading-snug">{s.label}</span>
        </motion.div>
      ))}
    </div>
  );
}

// ── PAGE ──────────────────────────────────────────────────────────────────────
export default function ModulesPage() {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const heroY       = useTransform(scrollYProgress, [0, 1], ["0%", "18%"]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.75], [1, 0]);

  return (
    <main className="relative">{/* overflow-x-hidden removido — quebraria o sticky do notebook */}

      {/* ── HERO ────────────────────────────────────────────────────────────── */}
      <section
        ref={heroRef}
        className="relative flex flex-col items-center justify-center min-h-[72vh] text-center overflow-hidden -mt-40 pt-40"
      >
        <GridLines
          className="opacity-15"
          style={{
            WebkitMaskImage: "radial-gradient(65% 65% at 50% 45%, #000 50%, transparent 100%)",
            maskImage:        "radial-gradient(65% 65% at 50% 45%, #000 50%, transparent 100%)",
          }}
        />

        {/* Orbs */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="pointer-events-none absolute top-[15%] left-1/2 -translate-x-1/2 w-[480px] h-[480px] rounded-full bg-primary/12 blur-[120px]"
        />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="pointer-events-none absolute bottom-[10%] right-[10%] w-52 h-52 rounded-full bg-primary/7 blur-[80px]"
        />

        <motion.div
          style={{ y: heroY, opacity: heroOpacity }}
          className="relative z-10 flex flex-col items-center gap-5 max-w-3xl mx-auto px-4"
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.88, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/30 bg-primary/10 backdrop-blur-sm text-xs font-medium text-primary"
          >
            <FontAwesomeIcon icon={faLayerGroup} className="text-[10px]" />
            Todos os módulos disponíveis
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
            className="text-5xl sm:text-6xl md:text-7xl font-black leading-[0.95] tracking-tight"
          >
            Tudo que você
            <br />
            <span className="text-primary">precisa.</span>
            <br />
            Num bot só.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25, duration: 0.55 }}
            className="text-foreground/55 text-sm md:text-base max-w-lg leading-relaxed"
          >
            11 módulos independentes e integrados para gerenciar, automatizar e monetizar seu servidor Discord — cada um pensado para o máximo de controle com o mínimo de esforço.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.45 }}
            className="flex flex-col sm:flex-row gap-3 mt-1"
          >
            <Button
              as={Link}
              href="/socials/discord"
              className="bg-primary hover:bg-primary/90 text-white font-semibold shadow-lg shadow-primary/20 flex items-center gap-2"
            >
              <FontAwesomeIcon icon={faDiscord} className="text-sm" />
              Começar agora
            </Button>
            <Button
              as={Link}
              href="/pricing"
              className="bg-transparent border border-foreground/10 text-foreground/70 hover:text-foreground hover:bg-foreground/5"
            >
              <span className="flex items-center gap-1.5">
                Ver planos
                <FontAwesomeIcon icon={faChevronRight} className="text-[10px]" />
              </span>
            </Button>
          </motion.div>
        </motion.div>

        {/* Scroll hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.0 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 6, 0] }}
            transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
            className="w-px h-10 bg-gradient-to-b from-foreground/20 to-transparent mx-auto"
          />
        </motion.div>
      </section>

      {/* ── STATS ───────────────────────────────────────────────────────────── */}
      <StatStrip />

      {/* ── MODULES SECTION ─────────────────────────────────────────────────── */}
      <section className="mt-24 md:mt-32 mb-4">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex items-center gap-1 mb-3">
            <FontAwesomeIcon icon={faRobot} className="text-primary text-[12px]" />
            <span className="text-primary/50 text-[12px]">|</span>
            <span className="text-primary font-semibold text-[12px]">Módulos do bot</span>
          </div>
          <h2 className="text-3xl md:text-5xl font-black leading-tight max-w-2xl">
            Explore cada <span className="text-primary">módulo</span>
          </h2>
          <p className="text-foreground/50 mt-3 text-sm max-w-lg">
            Role a página para virar as páginas do caderno e descobrir cada módulo.
          </p>
        </motion.div>
      </section>

      {/* ── 3D NOTEBOOK (scroll container — ocupa espaço vertical para drive animation) */}
      <Notebook3D modules={modules} />

      {/* ── CTA ─────────────────────────────────────────────────────────────── */}
      <section className="mt-24 md:mt-32">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="relative overflow-hidden rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-8 md:p-14 text-center"
        >
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2/3 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
          <div className="pointer-events-none absolute -top-24 -left-24 w-72 h-72 rounded-full bg-primary/10 blur-[80px]" />
          <div className="pointer-events-none absolute -bottom-20 -right-20 w-56 h-56 rounded-full bg-primary/6 blur-[70px]" />

          <div className="relative z-10 max-w-xl mx-auto flex flex-col items-center gap-5">
            <div className="flex items-center gap-1 mb-1">
              <FontAwesomeIcon icon={faStar} className="text-primary text-[12px]" />
              <span className="text-primary/50 text-[12px]">|</span>
              <span className="text-primary font-semibold text-[12px]">Tudo incluso</span>
            </div>

            <h2 className="text-3xl md:text-5xl font-black leading-tight">
              Pronto para ativar
              <br className="hidden md:block" />
              os <span className="text-primary">módulos?</span>
            </h2>

            <p className="text-foreground/55 text-sm max-w-md">
              Escolha um plano e tenha acesso a todos os módulos disponíveis para o seu servidor.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <Button
                as={Link}
                href="/socials/discord"
                className="bg-primary hover:bg-primary/90 text-white font-semibold shadow-lg shadow-primary/25 px-6"
              >
                <FontAwesomeIcon icon={faDiscord} className="text-sm" />
                Entrar no Discord
              </Button>
              <Button
                as={Link}
                href="/pricing"
                className="bg-transparent border border-foreground/10 text-foreground/70 hover:text-foreground hover:bg-foreground/5"
              >
                <span className="flex items-center gap-1.5">
                  Ver planos e preços
                  <FontAwesomeIcon icon={faChevronRight} className="text-[10px]" />
                </span>
              </Button>
            </div>

            <div className="flex flex-wrap justify-center gap-4 text-foreground/30 text-[11px] mt-1">
              {["11 módulos", "Painel unificado", "Suporte via Discord", "Configuração simples"].map((t, i) => (
                <span key={i} className="flex items-center gap-1.5">
                  <FontAwesomeIcon icon={faCircleCheck} className="text-primary/40 text-[9px]" />
                  {t}
                </span>
              ))}
            </div>
          </div>
        </motion.div>
      </section>

    </main>
  );
}