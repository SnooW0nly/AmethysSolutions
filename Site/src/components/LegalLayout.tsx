"use client";

import Link from "next/link";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChevronLeft, faCalendar } from "@fortawesome/free-solid-svg-icons";

interface LegalLayoutProps {
  title: string;
  subtitle?: string;
  updatedAt: string;
  badge?: string;
  children: React.ReactNode;
}

export default function LegalLayout({ title, subtitle, updatedAt, badge, children }: LegalLayoutProps) {
  return (
    <div className="max-w-3xl mx-auto">
      {/* Back link */}
      <Link
        href="/terms"
        className="inline-flex items-center gap-2 text-foreground/50 hover:text-foreground/80 text-[12px] transition-colors mb-6 group"
      >
        <FontAwesomeIcon icon={faChevronLeft} className="text-[10px] group-hover:-translate-x-0.5 transition-transform" />
        Voltar para Termos de Serviço
      </Link>

      {/* Header */}
      <div className="mb-8 space-y-3">
        {badge && (
          <span className="inline-block text-[10px] font-mono uppercase tracking-widest text-primary/80 border border-primary/20 bg-primary/5 px-2.5 py-1 rounded-sm">
            {badge}
          </span>
        )}
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        {subtitle && (
          <p className="text-foreground/60 text-sm leading-relaxed max-w-xl">{subtitle}</p>
        )}
        <div className="flex items-center gap-1.5 text-foreground/40 text-[11px] font-mono">
          <FontAwesomeIcon icon={faCalendar} className="text-[10px]" />
          <span>Última atualização: {updatedAt}</span>
        </div>
      </div>

      <hr className="border-foreground/10 mb-10" />

      {/* Content */}
      <div className="space-y-12 pb-10">
        {children}
      </div>
    </div>
  );
}

/* ── Sub-components for building legal content ── */

export function LegalSection({ number, title, children }: { number: string; title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <div className="flex items-baseline gap-3">
        <span className="text-[11px] font-mono text-primary/60 shrink-0">{number}</span>
        <h2 className="text-lg font-bold text-foreground/95 uppercase tracking-wide">{title}</h2>
      </div>
      <div className="space-y-3 pl-0">{children}</div>
    </section>
  );
}

export function LegalClause({ index, children }: { index: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3 group">
      <span className="text-[11px] font-mono text-foreground/30 shrink-0 mt-0.5 group-hover:text-primary/50 transition-colors select-none">
        {index}
      </span>
      <p className="text-sm text-foreground/75 leading-relaxed">{children}</p>
    </div>
  );
}

export function LegalSubSection({ number, title, children }: { number: string; title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3 mt-5">
      <div className="flex items-baseline gap-3">
        <span className="text-[11px] font-mono text-foreground/40 shrink-0">{number}</span>
        <h3 className="text-sm font-semibold text-foreground/80">{title}</h3>
      </div>
      <div className="space-y-3 pl-0">{children}</div>
    </div>
  );
}

export function LegalNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 border-l-2 border-primary/30 pl-4 py-1">
      <p className="text-[12px] text-foreground/50 italic leading-relaxed">{children}</p>
    </div>
  );
}