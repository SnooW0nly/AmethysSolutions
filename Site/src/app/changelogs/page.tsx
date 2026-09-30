"use client";

/**
 * src/app/changelogs/page.tsx
 * Fetch: GET /api/info/changelogs
 */

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faLayerGroup, faCalendar } from "@fortawesome/free-solid-svg-icons";
import GridLines from "@/components/GridLines";

// ── Types ─────────────────────────────────────────────────────────────────────

type ItemType = "new" | "improved" | "fixed";

type ChangelogItem = {
  _id: string;
  type: ItemType;
  title: string;
  description: string;
};

type Changelog = {
  _id: string;
  version: string;
  title: string;
  description?: string;
  items: ChangelogItem[];
  published: boolean;
  publishedAt?: string;
  createdAt: string;
};

// ── Custom SVG Icons ──────────────────────────────────────────────────────────

function IconNew({ size = 13 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="2" fill="currentColor" />
      <path d="M7 1.5V3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M7 10.5V12.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M1.5 7H3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M10.5 7H12.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M3.44 3.44L4.86 4.86" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <path d="M9.14 9.14L10.56 10.56" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <path d="M10.56 3.44L9.14 4.86" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <path d="M4.86 9.14L3.44 10.56" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function IconImproved({ size = 13 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none">
      <path d="M7 11.5V2.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M3.5 6L7 2.5L10.5 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3.5 9.5H10.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeOpacity="0.35" />
      <path d="M5 11.5H9" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeOpacity="0.18" />
    </svg>
  );
}

function IconFixed({ size = 13 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none">
      <path
        d="M10.5 3.5C10.5 3.5 11.2 5.6 9.9 6.9L6.1 10.7C4.8 12 3 11.5 3 11.5C3 11.5 2.5 9.7 3.8 8.4L7.6 4.6C8.9 3.3 10.5 3.5 10.5 3.5Z"
        stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"
      />
      <path d="M4.8 9.5L6.5 7.8" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeOpacity="0.4" />
      <circle cx="10.5" cy="3.5" r="1.1" fill="currentColor" opacity="0.45" />
    </svg>
  );
}

// ── Type Config ───────────────────────────────────────────────────────────────

type IconComponent = (props: { size?: number }) => React.JSX.Element;

const TYPE_CONFIG: Record<
  ItemType,
  {
    label: string;
    Icon: IconComponent;
    text: string;
    bg: string;
    border: string;
    bar: string;
    cardBg: string;
    cardBorder: string;
    sectionText: string;
    iconBox: string;
  }
> = {
  new: {
    label: "Novo",
    Icon: IconNew,
    text: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/25",
    bar: "bg-emerald-400",
    cardBg: "bg-emerald-500/[0.035]",
    cardBorder: "border-emerald-500/10",
    sectionText: "text-emerald-400",
    iconBox: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
  },
  improved: {
    label: "Melhorado",
    Icon: IconImproved,
    text: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/25",
    bar: "bg-blue-400",
    cardBg: "bg-blue-500/[0.035]",
    cardBorder: "border-blue-500/10",
    sectionText: "text-blue-400",
    iconBox: "bg-blue-500/10 border-blue-500/20 text-blue-400",
  },
  fixed: {
    label: "Corrigido",
    Icon: IconFixed,
    text: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/25",
    bar: "bg-amber-400",
    cardBg: "bg-amber-500/[0.035]",
    cardBorder: "border-amber-500/10",
    sectionText: "text-amber-400",
    iconBox: "bg-amber-500/10 border-amber-500/20 text-amber-400",
  },
};

// ── Pill badge ────────────────────────────────────────────────────────────────

function TypeBadge({ type, count }: { type: ItemType; count?: number }) {
  const cfg = TYPE_CONFIG[type];
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full border ${cfg.text} ${cfg.bg} ${cfg.border}`}>
      <span className="flex items-center justify-center">
        <cfg.Icon size={11} />
      </span>
      {cfg.label}
      {count !== undefined && count > 1 && (
        <span className="opacity-55 font-mono text-[10px]">×{count}</span>
      )}
    </span>
  );
}

// ── Section heading with line ─────────────────────────────────────────────────

function TypeSection({ type, items }: { type: ItemType; items: ChangelogItem[] }) {
  if (!items.length) return null;
  const cfg = TYPE_CONFIG[type];

  return (
    <div>
      {/* Heading */}
      <div className="flex items-center gap-2 mb-2.5">
        <div className={`flex items-center justify-center w-[22px] h-[22px] rounded-md border ${cfg.iconBox}`}>
          <cfg.Icon size={12} />
        </div>
        <span className={`text-[11px] font-bold uppercase tracking-[0.09em] ${cfg.sectionText}`}>
          {cfg.label}
        </span>
        <div className={`flex-1 h-px ${cfg.bar} opacity-12`} />
      </div>

      {/* Items */}
      <div className="space-y-2 pl-1">
        {items.map((item) => (
          <div
            key={item._id}
            className={`flex gap-3 p-3.5 rounded-xl border ${cfg.cardBg} ${cfg.cardBorder} group transition-all`}
          >
            <div className={`w-[3px] rounded-full shrink-0 self-stretch ${cfg.bar} opacity-45 group-hover:opacity-75 transition-opacity`} />
            <div className="min-w-0">
              <p className="text-sm font-semibold leading-snug text-foreground/90">
                {item.title}
              </p>
              {item.description && (
                <p className="text-foreground/42 text-xs mt-1 leading-relaxed">
                  {item.description}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Changelog Card ────────────────────────────────────────────────────────────

function ChangelogCard({ changelog, index, isLatest }: { changelog: Changelog; index: number; isLatest: boolean }) {
  const [expanded, setExpanded] = useState(isLatest);
  const date = changelog.publishedAt || changelog.createdAt;

  const grouped = {
    new: changelog.items.filter((i) => i.type === "new"),
    improved: changelog.items.filter((i) => i.type === "improved"),
    fixed: changelog.items.filter((i) => i.type === "fixed"),
  };
  const total = changelog.items.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.55, delay: index * 0.065, ease: [0.22, 1, 0.36, 1] }}
      className="relative"
    >
      {/* Timeline connector */}
      <div className="hidden md:block absolute left-[180px] top-0 bottom-0 w-px bg-gradient-to-b from-foreground/10 via-foreground/5 to-transparent pointer-events-none" />

      <div className="flex flex-col md:flex-row gap-5 md:gap-8">

        {/* Left meta */}
        <div className="md:w-44 shrink-0 flex flex-row md:flex-col items-center md:items-end justify-between md:justify-start gap-2 md:pt-2.5">
          <span className="text-foreground/30 text-[11px] font-mono whitespace-nowrap">
            {new Date(date).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" })}
          </span>
          <div className="flex items-center gap-1.5">
            {isLatest && (
              <span className="text-[9px] font-black text-white bg-primary px-2 py-0.5 rounded-full tracking-wide hidden md:block">
                ATUAL
              </span>
            )}
            <span className="text-xs font-black font-mono text-primary bg-primary/10 border border-primary/20 px-2.5 py-1 rounded-lg">
              {changelog.version}
            </span>
          </div>
        </div>

        {/* Timeline dot */}
        <div className="hidden md:flex items-start pt-3 shrink-0 z-10">
          <div className={`w-3 h-3 rounded-full border-2 border-background ${isLatest ? "bg-primary shadow-lg shadow-primary/40 scale-125" : "bg-foreground/18"}`} />
        </div>

        {/* Card */}
        <div className="flex-1 min-w-0 pb-10">
          <div className={`rounded-2xl border overflow-hidden transition-all ${isLatest ? "border-primary/14 bg-primary/[0.018]" : "border-foreground/8 bg-foreground/[0.012] hover:border-foreground/12"}`}>

            {/* Card header — always clickable */}
            <button
              onClick={() => setExpanded((p) => !p)}
              className="w-full flex items-start justify-between gap-4 px-5 py-4 text-left group cursor-pointer"
            >
              <div className="flex-1 min-w-0">
                <p className="font-bold text-[15px] leading-snug">{changelog.title}</p>
                {changelog.description && (
                  <p className="text-foreground/38 text-xs mt-1">{changelog.description}</p>
                )}
                {/* Collapsed: show badges */}
                {!expanded && total > 0 && (
                  <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
                    {(["new", "improved", "fixed"] as ItemType[]).map((t) => {
                      const cnt = grouped[t].length;
                      return cnt > 0 ? <TypeBadge key={t} type={t} count={cnt} /> : null;
                    })}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 mt-0.5 shrink-0">
                {!expanded && (
                  <span className="text-foreground/22 text-[10px] font-mono hidden sm:block">
                    {total} item{total !== 1 ? "s" : ""}
                  </span>
                )}
                <motion.div
                  animate={{ rotate: expanded ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                  className="w-6 h-6 rounded-lg border border-foreground/8 bg-foreground/[0.03] flex items-center justify-center flex-shrink-0"
                >
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="text-foreground/35">
                    <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </motion.div>
              </div>
            </button>

            {/* Expanded content */}
            <AnimatePresence initial={false}>
              {expanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                  className="overflow-hidden"
                >
                  <div className="px-5 pb-5 pt-2 border-t border-foreground/6 space-y-5">
                    {/* Summary badges */}
                    {total > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-1">
                        {(["new", "improved", "fixed"] as ItemType[]).map((t) => {
                          const cnt = grouped[t].length;
                          return cnt > 0 ? <TypeBadge key={t} type={t} count={cnt} /> : null;
                        })}
                      </div>
                    )}

                    {total === 0 && (
                      <p className="text-foreground/22 text-xs italic">Sem itens nesta versão.</p>
                    )}

                    {(["new", "improved", "fixed"] as ItemType[]).map((t) => (
                      <TypeSection key={t} type={t} items={grouped[t]} />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function SkeletonCard({ i }: { i: number }) {
  return (
    <div className="flex flex-col md:flex-row gap-5 md:gap-8 animate-pulse" style={{ animationDelay: `${i * 0.1}s` }}>
      <div className="md:w-44 shrink-0 flex flex-col items-end gap-2 pt-2">
        <div className="h-3 w-20 bg-foreground/6 rounded-full" />
        <div className="h-7 w-14 bg-foreground/8 rounded-lg" />
      </div>
      <div className="hidden md:block w-3 h-3 rounded-full bg-foreground/8 mt-3 shrink-0" />
      <div className="flex-1 pb-10">
        <div className="rounded-2xl border border-foreground/8 p-5 space-y-3">
          <div className="h-4 w-2/5 bg-foreground/8 rounded-lg" />
          <div className="h-3 w-3/5 bg-foreground/5 rounded-full" />
          <div className="flex gap-2 pt-1">
            <div className="h-6 w-16 bg-foreground/6 rounded-full" />
            <div className="h-6 w-20 bg-foreground/6 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── PAGE ──────────────────────────────────────────────────────────────────────

export default function ChangelogsPage() {
  const [changelogs, setChangelogs] = useState<Changelog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/info/changelogs")
      .then((r) => r.json())
      .then((data) => {
        if (data.success) setChangelogs(data.data);
        else setError("Não foi possível carregar os changelogs.");
      })
      .catch(() => setError("Erro de conexão."))
      .finally(() => setLoading(false));
  }, []);

  const totalNew = changelogs.reduce((a, c) => a + c.items.filter((i) => i.type === "new").length, 0);
  const totalImproved = changelogs.reduce((a, c) => a + c.items.filter((i) => i.type === "improved").length, 0);
  const totalFixed = changelogs.reduce((a, c) => a + c.items.filter((i) => i.type === "fixed").length, 0);

  return (
    <main className="relative overflow-x-hidden">
      {/* ── Hero ── */}
      <section className="relative flex flex-col items-center justify-center min-h-[52vh] text-center overflow-hidden -mt-40 pt-40">
        <GridLines
          className="opacity-[0.07]"
          style={{
            WebkitMaskImage: "radial-gradient(55% 55% at 50% 50%, #000 40%, transparent 100%)",
            maskImage: "radial-gradient(55% 55% at 50% 50%, #000 40%, transparent 100%)",
          }}
        />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
          className="pointer-events-none absolute top-1/4 left-1/2 -translate-x-1/2 w-[380px] h-[380px] rounded-full bg-primary/7 blur-[110px]"
        />

        <motion.div
          initial={{ opacity: 0, y: 22 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.68, ease: [0.22, 1, 0.36, 1] }}
          className="relative z-10 flex flex-col items-center gap-4 max-w-2xl mx-auto px-4"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/28 bg-primary/8 text-xs font-semibold text-primary"
          >
            <FontAwesomeIcon icon={faLayerGroup} className="text-[10px]" />
            Histórico de Atualizações
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.16, duration: 0.62 }}
            className="text-5xl sm:text-6xl md:text-7xl font-black leading-[0.93] tracking-tight"
          >
            O que há de <span className="text-primary">novo?</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.28, duration: 0.5 }}
            className="text-foreground/42 text-sm md:text-base max-w-md leading-relaxed"
          >
            Novas funções, melhorias e correções do Amethys por versão — sempre atualizadas.
          </motion.p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 6, 0] }}
            transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
            className="w-px h-10 bg-gradient-to-b from-foreground/15 to-transparent mx-auto"
          />
        </motion.div>
      </section>

      {/* ── Stats ── */}
      {!loading && !error && changelogs.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-16 mt-4"
        >
          {/* Versões */}
          <div className="flex flex-col items-center gap-1.5 py-5 px-4 rounded-xl border border-foreground/8 bg-foreground/[0.02] text-center">
            <span className="text-3xl font-black text-foreground tabular-nums">{changelogs.length}</span>
            <span className="text-foreground/35 text-[11px]">Versões</span>
          </div>
          {/* New */}
          <div className="flex flex-col items-center gap-1.5 py-5 px-4 rounded-xl border border-emerald-500/18 bg-emerald-500/[0.04] text-center">
            <span className="text-emerald-400 mb-0.5"><IconNew size={15} /></span>
            <span className="text-3xl font-black text-emerald-400 tabular-nums">{totalNew}</span>
            <span className="text-foreground/35 text-[11px]">Novas funções</span>
          </div>
          {/* Improved */}
          <div className="flex flex-col items-center gap-1.5 py-5 px-4 rounded-xl border border-blue-500/18 bg-blue-500/[0.04] text-center">
            <span className="text-blue-400 mb-0.5"><IconImproved size={15} /></span>
            <span className="text-3xl font-black text-blue-400 tabular-nums">{totalImproved}</span>
            <span className="text-foreground/35 text-[11px]">Melhorias</span>
          </div>
          {/* Fixed */}
          <div className="flex flex-col items-center gap-1.5 py-5 px-4 rounded-xl border border-amber-500/18 bg-amber-500/[0.04] text-center">
            <span className="text-amber-400 mb-0.5"><IconFixed size={15} /></span>
            <span className="text-3xl font-black text-amber-400 tabular-nums">{totalFixed}</span>
            <span className="text-foreground/35 text-[11px]">Correções</span>
          </div>
        </motion.div>
      )}

      {/* ── List ── */}
      <section className="max-w-3xl mx-auto">
        {!loading && !error && changelogs.length > 0 && (
          <div className="flex items-center gap-2 mb-10">
            <FontAwesomeIcon icon={faCalendar} className="text-primary text-[11px]" />
            <span className="text-primary/45 text-[11px]">|</span>
            <span className="text-primary font-semibold text-[11px]">Versões lançadas</span>
          </div>
        )}

        {error && (
          <div className="text-center py-16 border border-red-500/12 bg-red-500/[0.02] rounded-2xl">
            <p className="text-foreground/38 text-sm">{error}</p>
          </div>
        )}

        {loading && [0, 1, 2].map((i) => <SkeletonCard key={i} i={i} />)}

        {!loading && !error && changelogs.length === 0 && (
          <div className="text-center py-24 border border-dashed border-foreground/8 rounded-2xl">
            <FontAwesomeIcon icon={faLayerGroup} className="text-foreground/12 text-3xl mb-3" />
            <p className="text-foreground/25 text-sm">Nenhum changelog publicado ainda.</p>
          </div>
        )}

        {!loading && !error && changelogs.map((cl, i) => (
          <ChangelogCard key={cl._id} changelog={cl} index={i} isLatest={i === 0} />
        ))}
      </section>
    </main>
  );
}