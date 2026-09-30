"use client";

import { useEffect, useState, useRef } from "react";

type Partnership = {
  _id: string;
  name: string;
  shortDescription?: string;
  description?: string;
  logoUrl?: string;
  bannerUrl?: string;
  websiteUrl?: string;
  active: boolean;
};

function PartnerCard({ partner }: { partner: Partnership }) {
  return (
    <a
      href={partner.websiteUrl ?? "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="shrink-0 flex items-center gap-3 px-4 py-3 rounded-xl border border-white/[0.07] bg-white/[0.03] hover:bg-white/[0.07] hover:border-white/[0.14] transition-all duration-200 cursor-pointer"
      style={{ textDecoration: "none", minWidth: "180px", maxWidth: "220px" }}
    >
      {partner.logoUrl ? (
        <img
          src={partner.logoUrl}
          alt={partner.name}
          width={36}
          height={36}
          className="w-9 h-9 rounded-lg object-cover flex-shrink-0 border border-white/10"
        />
      ) : (
        <div className="w-9 h-9 rounded-lg bg-white/[0.08] flex items-center justify-center flex-shrink-0 border border-white/10">
          <span className="text-[11px] font-bold text-foreground/40">
            {partner.name.slice(0, 2).toUpperCase()}
          </span>
        </div>
      )}
      <div className="flex flex-col min-w-0">
        <span className="text-[10px] uppercase tracking-widest text-foreground/30 font-medium">parceiro</span>
        <span className="text-sm font-semibold text-foreground/80 truncate">{partner.name}</span>
        {(partner.shortDescription || partner.description) && (
          <span className="text-[11px] text-foreground/40 truncate">
            {partner.shortDescription || partner.description}
          </span>
        )}
      </div>
    </a>
  );
}

export function PartnersMarquee() {
  const [partners, setPartners] = useState<Partnership[] | null>(null);

  useEffect(() => {
    fetch("/api/info/partnerships")
      .then((r) => r.json())
      .then((json) => {
        const list = Array.isArray(json?.data)
          ? json.data.filter((p: Partnership) => p.active)
          : Array.isArray(json)
          ? json.filter((p: Partnership) => p.active)
          : [];
        setPartners(list);
      })
      .catch(() => setPartners([]));
  }, []);

  // Ainda carregando — não renderiza nada
  if (partners === null) return null;
  // Sem parceiros — não renderiza nada
  if (partners.length === 0) return null;

  // Duplica para loop infinito suave
  const items = [...partners, ...partners, ...partners];

  return (
    <div className="mt-10 w-full">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <p className="text-xs uppercase tracking-widest text-foreground/40 font-semibold">
          Nossos Parceiros
        </p>
        <div className="flex-1 h-px bg-foreground/10" />
      </div>

      {/* Carrossel */}
      <>
        <style>{`
          @keyframes partners-scroll {
            0%   { transform: translateX(0); }
            100% { transform: translateX(calc(-100% / 3)); }
          }
          .partners-track {
            animation: partners-scroll 28s linear infinite;
            will-change: transform;
          }
          .partners-track:hover {
            animation-play-state: paused;
          }
        `}</style>

        <div
          className="relative w-full overflow-hidden rounded-xl border border-white/[0.05] bg-white/[0.02]"
          style={{ padding: "14px 0" }}
        >
          {/* Fade left */}
          <div
            className="pointer-events-none absolute top-0 left-0 bottom-0 z-10"
            style={{
              width: "60px",
              background: "linear-gradient(to right, rgba(10,10,10,0.9) 0%, transparent 100%)",
            }}
          />
          {/* Fade right */}
          <div
            className="pointer-events-none absolute top-0 right-0 bottom-0 z-10"
            style={{
              width: "60px",
              background: "linear-gradient(to left, rgba(10,10,10,0.9) 0%, transparent 100%)",
            }}
          />

          <div className="partners-track flex flex-row gap-3 w-max px-4">
            {items.map((p, i) => (
              <PartnerCard key={`${p._id}-${i}`} partner={p} />
            ))}
          </div>
        </div>
      </>
    </div>
  );
}