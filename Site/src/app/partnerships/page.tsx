"use client";

import { useEffect, useState } from "react";
import { Chip, Button, Spinner } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faHandshake,
  faGlobe,
  faTag,
  faStar,
  faCheck,
  faDiscord,
  faArrowUpRightFromSquare,
  faCopy,
} from "@fortawesome/free-solid-svg-icons";
import { faDiscord as faDiscordBrand } from "@fortawesome/free-brands-svg-icons";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Partnership {
  _id: string;
  name: string;
  slug: string;
  description: string;
  shortDescription?: string;
  logoUrl?: string;
  bannerUrl?: string;
  websiteUrl?: string;
  discordUrl?: string;
  category: string;
  tags: string[];
  benefits: string[];
  couponCode?: string;
  couponDescription?: string;
  featured: boolean;
  active: boolean;
  order: number;
}

interface PartnershipsData {
  partnerships: Partnership[];
  grouped: Record<string, Partnership[]>;
  featured: Partnership[];
  total: number;
}

const CATEGORY_LABELS: Record<string, string> = {
  hosting: "Hospedagem",
  bot: "Bot",
  community: "Comunidade",
  tool: "Ferramenta",
  service: "Serviço",
  other: "Outro",
};

const CATEGORY_COLORS: Record<
  string,
  "primary" | "success" | "warning" | "danger" | "secondary" | "default"
> = {
  hosting: "primary",
  bot: "secondary",
  community: "success",
  tool: "warning",
  service: "danger",
  other: "default",
};

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function PartnershipsPage() {
  const [data, setData] = useState<PartnershipsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("all");

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await fetch("/api/info/partnerships", { cache: "no-store" });
        if (!res.ok) throw new Error("Erro ao carregar parcerias");
        const json = await res.json();
        setData(json);
      } catch (e: any) {
        setError(e?.message || "Erro ao carregar parcerias");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const categories = data
    ? Object.keys(data.grouped).filter((k) => data.grouped[k].length > 0)
    : [];

  const displayed =
    activeCategory === "all"
      ? data?.partnerships ?? []
      : data?.grouped[activeCategory] ?? [];

  const featured = data?.featured ?? [];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center text-foreground/60">
          <FontAwesomeIcon icon={faHandshake} className="text-4xl mb-3 opacity-30" />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-12 py-8">
      {/* ── Hero ── */}
      <section className="text-center flex flex-col items-center gap-4 max-w-2xl mx-auto px-4">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
          <FontAwesomeIcon icon={faHandshake} className="text-primary text-3xl" />
        </div>
        <h1 className="text-4xl font-bold">Parcerias</h1>
        <p className="text-foreground/60 text-lg leading-relaxed">
          Conheça nossos parceiros oficiais e aproveite os benefícios exclusivos
          disponíveis para a nossa comunidade.
        </p>
      </section>

      {/* ── Featured ── */}
      {featured.length > 0 && (
        <section className="flex flex-col gap-4 max-w-6xl mx-auto w-full px-4">
          <div className="flex items-center gap-2">
            <FontAwesomeIcon icon={faStar} className="text-yellow-400" />
            <h2 className="text-xl font-semibold">Parcerias em Destaque</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {featured.map((p) => (
              <FeaturedCard key={p._id} partnership={p} />
            ))}
          </div>
        </section>
      )}

      {/* ── Category Tabs ── */}
      {categories.length > 1 && (
        <section className="max-w-6xl mx-auto w-full px-4">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveCategory("all")}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                activeCategory === "all"
                  ? "bg-primary text-white"
                  : "bg-foreground/5 text-foreground/70 hover:bg-foreground/10"
              }`}
            >
              Todos ({data?.total ?? 0})
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  activeCategory === cat
                    ? "bg-primary text-white"
                    : "bg-foreground/5 text-foreground/70 hover:bg-foreground/10"
                }`}
              >
                {CATEGORY_LABELS[cat] ?? cat} ({data?.grouped[cat]?.length ?? 0})
              </button>
            ))}
          </div>
        </section>
      )}

      {/* ── Partnership Grid ── */}
      <section className="max-w-6xl mx-auto w-full px-4">
        {displayed.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-foreground/40">
            <FontAwesomeIcon icon={faHandshake} className="text-5xl mb-4" />
            <p>Nenhuma parceria encontrada.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {displayed.map((p) => (
              <PartnershipCard key={p._id} partnership={p} />
            ))}
          </div>
        )}
      </section>

      {/* ── Become a Partner CTA ── */}
      <section className="max-w-2xl mx-auto w-full px-4 text-center">
        <div className="rounded-2xl border border-foreground/10 bg-foreground/3 p-8 flex flex-col items-center gap-4">
          <FontAwesomeIcon icon={faHandshake} className="text-primary text-3xl" />
          <h3 className="text-xl font-semibold">Quer ser nosso parceiro?</h3>
          <p className="text-foreground/60 text-sm leading-relaxed">
            Entre em contato com a nossa equipe e saiba como se tornar um
            parceiro oficial e alcançar nossa comunidade.
          </p>
          <Button
            color="primary"
            variant="flat"
            startContent={<FontAwesomeIcon icon={faDiscordBrand} />}
            as="a"
            href="https://discord.gg/seu-servidor"
            target="_blank"
          >
            Falar com a equipe
          </Button>
        </div>
      </section>
    </div>
  );
}

// ─── Featured Card ────────────────────────────────────────────────────────────

function FeaturedCard({ partnership: p }: { partnership: Partnership }) {
  const [copied, setCopied] = useState(false);

  const copyCoupon = async () => {
    if (!p.couponCode) return;
    await navigator.clipboard.writeText(p.couponCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative rounded-2xl border border-yellow-400/20 bg-gradient-to-br from-yellow-400/5 via-transparent to-transparent overflow-hidden flex flex-col">
      {/* Banner */}
      {p.bannerUrl && (
        <div className="h-28 overflow-hidden">
          <img
            src={p.bannerUrl}
            alt={`${p.name} banner`}
            className="w-full h-full object-cover"
            onError={(e) => ((e.target as HTMLImageElement).parentElement!.style.display = "none")}
          />
        </div>
      )}

      <div className="p-5 flex flex-col gap-3 flex-1">
        {/* Header */}
        <div className="flex items-start gap-3">
          {p.logoUrl ? (
            <img
              src={p.logoUrl}
              alt={p.name}
              className="w-12 h-12 rounded-xl object-cover border border-foreground/10 flex-shrink-0"
              onError={(e) => ((e.target as HTMLImageElement).style.display = "none")}
            />
          ) : (
            <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
              <FontAwesomeIcon icon={faHandshake} className="text-primary" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <h3 className="font-bold text-base">{p.name}</h3>
              <FontAwesomeIcon icon={faStar} className="text-yellow-400 text-xs" />
            </div>
            <Chip
              size="sm"
              color={CATEGORY_COLORS[p.category] ?? "default"}
              variant="flat"
              className="mt-0.5"
            >
              {CATEGORY_LABELS[p.category] ?? p.category}
            </Chip>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-foreground/70 leading-relaxed line-clamp-3">
          {p.shortDescription || p.description}
        </p>

        {/* Benefits */}
        {p.benefits.length > 0 && (
          <ul className="flex flex-col gap-1">
            {p.benefits.slice(0, 3).map((b, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-foreground/70">
                <FontAwesomeIcon icon={faCheck} className="text-success mt-0.5 flex-shrink-0" />
                <span>{b}</span>
              </li>
            ))}
            {p.benefits.length > 3 && (
              <li className="text-xs text-foreground/40 ml-5">
                +{p.benefits.length - 3} mais benefícios
              </li>
            )}
          </ul>
        )}

        {/* Coupon */}
        {p.couponCode && (
          <button
            onClick={copyCoupon}
            className="flex items-center gap-2 bg-primary/10 border border-primary/20 rounded-xl px-3 py-2 hover:bg-primary/15 transition-colors text-left w-full"
          >
            <FontAwesomeIcon icon={faTag} className="text-primary text-sm" />
            <div className="flex-1 min-w-0">
              <span className="font-mono font-bold text-primary text-sm">{p.couponCode}</span>
              {p.couponDescription && (
                <p className="text-[11px] text-foreground/50">{p.couponDescription}</p>
              )}
            </div>
            <FontAwesomeIcon
              icon={copied ? faCheck : faCopy}
              className={`text-xs ${copied ? "text-success" : "text-foreground/40"}`}
            />
          </button>
        )}

        {/* Actions */}
        <div className="flex gap-2 mt-auto pt-1">
          {p.websiteUrl && (
            <Button
              size="sm"
              color="primary"
              variant="flat"
              as="a"
              href={p.websiteUrl}
              target="_blank"
              rel="noopener noreferrer"
              startContent={<FontAwesomeIcon icon={faGlobe} />}
              className="flex-1"
            >
              Visitar Site
            </Button>
          )}
          {p.discordUrl && (
            <Button
              size="sm"
              variant="flat"
              as="a"
              href={p.discordUrl}
              target="_blank"
              rel="noopener noreferrer"
              isIconOnly
              title="Discord"
            >
              <FontAwesomeIcon icon={faDiscordBrand} />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Regular Partnership Card ─────────────────────────────────────────────────

function PartnershipCard({ partnership: p }: { partnership: Partnership }) {
  const [copied, setCopied] = useState(false);

  const copyCoupon = async () => {
    if (!p.couponCode) return;
    await navigator.clipboard.writeText(p.couponCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-2xl border border-foreground/10 bg-foreground/2 hover:bg-foreground/4 hover:border-foreground/20 transition-all flex flex-col overflow-hidden">
      {/* Banner */}
      {p.bannerUrl && (
        <div className="h-20 overflow-hidden bg-foreground/5">
          <img
            src={p.bannerUrl}
            alt={`${p.name} banner`}
            className="w-full h-full object-cover opacity-80"
            onError={(e) => ((e.target as HTMLImageElement).parentElement!.style.display = "none")}
          />
        </div>
      )}

      <div className="p-5 flex flex-col gap-3 flex-1">
        {/* Header */}
        <div className="flex items-center gap-3">
          {p.logoUrl ? (
            <img
              src={p.logoUrl}
              alt={p.name}
              className="w-10 h-10 rounded-xl object-cover border border-foreground/10 flex-shrink-0"
              onError={(e) => ((e.target as HTMLImageElement).style.display = "none")}
            />
          ) : (
            <div className="w-10 h-10 rounded-xl bg-foreground/5 border border-foreground/10 flex items-center justify-center flex-shrink-0">
              <FontAwesomeIcon icon={faHandshake} className="text-foreground/40" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <h3 className="font-semibold text-sm truncate">{p.name}</h3>
              {p.featured && (
                <FontAwesomeIcon icon={faStar} className="text-yellow-400 text-[10px]" />
              )}
            </div>
            <Chip
              size="sm"
              color={CATEGORY_COLORS[p.category] ?? "default"}
              variant="flat"
              className="mt-0.5 scale-90 origin-left"
            >
              {CATEGORY_LABELS[p.category] ?? p.category}
            </Chip>
          </div>
        </div>

        {/* Description */}
        <p className="text-xs text-foreground/60 leading-relaxed line-clamp-2">
          {p.shortDescription || p.description}
        </p>

        {/* Tags */}
        {p.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {p.tags.slice(0, 4).map((t) => (
              <span
                key={t}
                className="text-[10px] bg-foreground/5 border border-foreground/10 rounded-full px-2 py-0.5 text-foreground/50"
              >
                {t}
              </span>
            ))}
            {p.tags.length > 4 && (
              <span className="text-[10px] text-foreground/30">+{p.tags.length - 4}</span>
            )}
          </div>
        )}

        {/* Benefits */}
        {p.benefits.length > 0 && (
          <ul className="flex flex-col gap-1">
            {p.benefits.slice(0, 2).map((b, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[11px] text-foreground/60">
                <FontAwesomeIcon icon={faCheck} className="text-success mt-0.5 flex-shrink-0" />
                <span className="line-clamp-1">{b}</span>
              </li>
            ))}
          </ul>
        )}

        {/* Coupon */}
        {p.couponCode && (
          <button
            onClick={copyCoupon}
            className="flex items-center gap-2 bg-primary/5 border border-primary/15 rounded-lg px-2.5 py-1.5 hover:bg-primary/10 transition-colors text-left w-full"
          >
            <FontAwesomeIcon icon={faTag} className="text-primary text-xs" />
            <span className="font-mono font-bold text-primary text-xs flex-1">{p.couponCode}</span>
            <FontAwesomeIcon
              icon={copied ? faCheck : faCopy}
              className={`text-[10px] ${copied ? "text-success" : "text-foreground/30"}`}
            />
          </button>
        )}

        {/* Actions */}
        <div className="flex gap-2 mt-auto pt-2 border-t border-foreground/5">
          {p.websiteUrl && (
            <Button
              size="sm"
              variant="light"
              as="a"
              href={p.websiteUrl}
              target="_blank"
              rel="noopener noreferrer"
              startContent={<FontAwesomeIcon icon={faArrowUpRightFromSquare} className="text-xs" />}
              className="flex-1 text-xs"
            >
              Visitar
            </Button>
          )}
          {p.discordUrl && (
            <Button
              size="sm"
              variant="light"
              as="a"
              href={p.discordUrl}
              target="_blank"
              rel="noopener noreferrer"
              isIconOnly
              title="Discord"
            >
              <FontAwesomeIcon icon={faDiscordBrand} className="text-sm" />
            </Button>
          )}
          {!p.websiteUrl && !p.discordUrl && (
            <span className="text-xs text-foreground/30 py-1">Sem links disponíveis</span>
          )}
        </div>
      </div>
    </div>
  );
}