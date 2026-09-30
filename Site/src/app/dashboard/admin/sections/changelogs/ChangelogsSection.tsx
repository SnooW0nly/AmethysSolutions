"use client";

/**
 * src/app/dashboard/admin/sections/changelogs/ChangelogsSection.tsx
 */

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, Edit2, Trash2, Send, Eye, EyeOff, RefreshCw,
  ChevronLeft, ChevronUp, ChevronDown, X, FileText,
  CheckCircle, XCircle, Settings, Globe, Sparkles,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

export type ItemType = "new" | "improved" | "fixed";

export type ChangelogItem = {
  _id?: string;
  type: ItemType;
  title: string;
  description: string;
};

export type WebhookConfig = {
  webhookUrl?: string;
  coverImageUrl?: string;
  accentColorMain?: number;
  accentColorPromo?: number;
  promoText?: string;
  promoButtonLabel?: string;
  promoButtonUrl?: string;
  emojiNew?: string;
  emojiImproved?: string;
  emojiFixed?: string;
  sentAt?: string | null;
};

export type Changelog = {
  _id: string;
  version: string;
  title: string;
  description?: string;
  items: ChangelogItem[];
  published: boolean;
  publishedAt?: string;
  webhookConfig?: WebhookConfig;
  createdAt: string;
  updatedAt: string;
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

type IconComp = (props: { size?: number }) => React.JSX.Element;

// ── Type config ───────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<
  ItemType,
  {
    label: string;
    Icon: IconComp;
    text: string;
    bg: string;
    border: string;
    bar: string;
    cardBg: string;
    cardBorder: string;
    pillClass: string;
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
    pillClass: "text-emerald-400 bg-emerald-500/10 border-emerald-500/25",
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
    pillClass: "text-blue-400 bg-blue-500/10 border-blue-500/25",
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
    pillClass: "text-amber-400 bg-amber-500/10 border-amber-500/25",
    iconBox: "bg-amber-500/10 border-amber-500/20 text-amber-400",
  },
};

// ── Type Pill ─────────────────────────────────────────────────────────────────

function TypePill({ type }: { type: ItemType }) {
  const cfg = TYPE_CONFIG[type];
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full border ${cfg.pillClass}`}>
      <span className="flex items-center justify-center"><cfg.Icon size={11} /></span>
      {cfg.label}
    </span>
  );
}

// ── Type Selector (button group) ──────────────────────────────────────────────

function TypeSelector({ value, onChange }: { value: ItemType; onChange: (t: ItemType) => void }) {
  return (
    <div className="flex items-center gap-1">
      {(["new", "improved", "fixed"] as ItemType[]).map((t) => {
        const cfg = TYPE_CONFIG[t];
        const active = value === t;
        return (
          <button
            key={t}
            type="button"
            onClick={() => onChange(t)}
            className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1.5 rounded-lg border transition-all ${
              active
                ? `${cfg.pillClass} shadow-sm`
                : "text-foreground/35 bg-foreground/[0.03] border-foreground/8 hover:text-foreground/60 hover:bg-foreground/[0.06]"
            }`}
          >
            <span className="flex items-center justify-center">
              <cfg.Icon size={11} />
            </span>
            {cfg.label}
          </button>
        );
      })}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function numToHex(n: number): string {
  return "#" + (n >>> 0).toString(16).padStart(6, "0");
}
function hexToNum(h: string): number {
  return parseInt(h.replace("#", ""), 16) || 0;
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ toast }: { toast: { type: "success" | "error"; msg: string } | null }) {
  return (
    <AnimatePresence>
      {toast && (
        <motion.div
          initial={{ opacity: 0, y: -16, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -16, scale: 0.95 }}
          className={`fixed top-4 right-4 z-[200] flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-2xl text-sm font-medium backdrop-blur-md ${
            toast.type === "success"
              ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
              : "bg-red-500/15 border-red-500/30 text-red-300"
          }`}
        >
          {toast.type === "success"
            ? <CheckCircle className="w-4 h-4 flex-shrink-0" />
            : <XCircle className="w-4 h-4 flex-shrink-0" />}
          {toast.msg}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ── Discord Preview ───────────────────────────────────────────────────────────

function DiscordPreview({
  description,
  items,
  cfg,
}: {
  description?: string;
  items: ChangelogItem[];
  cfg: WebhookConfig;
}) {
  const mainColor = numToHex(cfg.accentColorMain ?? 0xc400c4);
  const promoColor = numToHex(cfg.accentColorPromo ?? 0xa61fe3);

  const grouped = {
    new: items.filter((i) => i.type === "new"),
    improved: items.filter((i) => i.type === "improved"),
    fixed: items.filter((i) => i.type === "fixed"),
  };

  return (
    <div className="bg-[#313338] rounded-xl p-4 space-y-2.5 text-sm select-none">
      {/* Bot row */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-full bg-[#8a00c4]/30 flex items-center justify-center text-xs font-black text-[#c084fc]">A</div>
        <div className="flex items-center gap-1.5">
          <span className="text-white text-xs font-semibold">Amethys</span>
          <span className="text-[10px] text-white bg-[#5865f2] px-1.5 py-0.5 rounded-sm font-medium">BOT</span>
        </div>
        <span className="ml-auto text-[#4e5058] text-[10px] font-mono">Hoje às 12:00</span>
      </div>

      {/* Main container */}
      <div className="rounded-lg overflow-hidden" style={{ borderLeft: `4px solid ${mainColor}` }}>
        <div className="bg-[#2b2d31] p-4 space-y-3">
          {cfg.coverImageUrl && (
            <img src={cfg.coverImageUrl} alt="" className="w-full h-16 object-cover rounded-md"
              onError={(e) => (e.currentTarget.style.display = "none")} />
          )}

          <div className="pb-2 border-b border-white/8">
            <p className="text-white font-bold text-sm">🔔 Atualização</p>
            <p className="text-[#b5bac1] text-xs mt-0.5">
              • Nova atualização na Amethys Solutions{description ? ` — ${description}` : ""}
            </p>
          </div>

          {items.length === 0 ? (
            <p className="text-[#4e5058] text-xs italic">Adicione itens para ver o preview</p>
          ) : (
            <div className="space-y-3">
              {(["new", "improved", "fixed"] as ItemType[]).map((t) => {
                const list = grouped[t];
                if (!list.length) return null;
                const cfg2 = TYPE_CONFIG[t];
                return (
                  <div key={t}>
                    {list.map((item, i) => (
                      <div key={i} className="mb-2">
                        <div className="flex items-center gap-1.5">
                          {/* Custom icon in preview — matches web rendering */}
                          <span className={`${cfg2.text} flex items-center`}>
                            <cfg2.Icon size={12} />
                          </span>
                          <p className="text-white font-semibold text-xs leading-snug">{item.title || "…"}</p>
                        </div>
                        <p className="text-[#b5bac1] text-[11px] mt-0.5 pl-[18px]">╰ {item.description || "…"}</p>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Promo container */}
      {(cfg.promoText || cfg.promoButtonUrl) && (
        <div className="rounded-lg overflow-hidden" style={{ borderLeft: `4px solid ${promoColor}` }}>
          <div className="bg-[#2b2d31] p-3 space-y-2">
            {cfg.promoText && <p className="text-[#b5bac1] text-[11px]">{cfg.promoText}</p>}
            {cfg.promoButtonUrl && (
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#4e5058] rounded text-white text-xs font-medium">
                <Globe className="w-3 h-3" />
                {cfg.promoButtonLabel || "Saiba mais"}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Item Row ──────────────────────────────────────────────────────────────────

function ItemRow({ item, index, total, onChange, onDelete, onMove }: {
  item: ChangelogItem; index: number; total: number;
  onChange: (it: ChangelogItem) => void;
  onDelete: () => void;
  onMove: (dir: -1 | 1) => void;
}) {
  const cfg = TYPE_CONFIG[item.type];
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="bg-foreground/[0.03] border border-foreground/10 rounded-xl p-4 space-y-3 group"
    >
      <div className="flex items-center gap-3 flex-wrap">
        <TypeSelector value={item.type} onChange={(t) => onChange({ ...item, type: t })} />
        <span className="text-foreground/20 text-[10px] font-mono ml-1">#{index + 1}</span>
        <div className="flex-1" />
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={() => onMove(-1)} disabled={index === 0}
            className="w-6 h-6 rounded flex items-center justify-center text-foreground/35 hover:text-foreground hover:bg-foreground/10 disabled:opacity-20 disabled:cursor-not-allowed transition-all">
            <ChevronUp className="w-3 h-3" />
          </button>
          <button onClick={() => onMove(1)} disabled={index === total - 1}
            className="w-6 h-6 rounded flex items-center justify-center text-foreground/35 hover:text-foreground hover:bg-foreground/10 disabled:opacity-20 disabled:cursor-not-allowed transition-all">
            <ChevronDown className="w-3 h-3" />
          </button>
          <button onClick={onDelete}
            className="w-6 h-6 rounded flex items-center justify-center text-foreground/30 hover:text-red-400 hover:bg-red-500/10 transition-all ml-0.5">
            <X className="w-3 h-3" />
          </button>
        </div>
      </div>

      <input
        value={item.title}
        onChange={(e) => onChange({ ...item, title: e.target.value })}
        placeholder="Título do item..."
        className="w-full px-3 py-2 bg-background/50 border border-foreground/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary transition-all placeholder:text-foreground/20"
      />
      <textarea
        value={item.description}
        onChange={(e) => onChange({ ...item, description: e.target.value })}
        placeholder="Descrição do que foi feito..."
        rows={2}
        className="w-full px-3 py-2 bg-background/50 border border-foreground/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary transition-all resize-none placeholder:text-foreground/20"
      />
    </motion.div>
  );
}

// ── Collapsible ───────────────────────────────────────────────────────────────

function Collapsible({ title, icon: Icon, badge, children }: {
  title: string; icon: any; badge?: React.ReactNode; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-background/50 border border-foreground/10 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-foreground/[0.02] transition-all text-left"
      >
        <div className="flex items-center gap-2.5">
          <Icon className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold">{title}</span>
          {badge}
        </div>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown className="w-4 h-4 text-foreground/35" />
        </motion.div>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="border-t border-foreground/8 px-5 pb-5 pt-4 space-y-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── AI Generate Modal ─────────────────────────────────────────────────────────

function AIGenerateModal({
  onClose,
  onApply,
}: {
  onClose: () => void;
  onApply: (items: ChangelogItem[]) => void;
}) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const systemPrompt = `Você é um assistente que gera itens de changelog para um software.
O usuário vai descrever o que foi feito na atualização e você deve retornar APENAS um JSON válido (sem markdown, sem backticks, sem explicações) com o seguinte formato:
[
  { "type": "new" | "improved" | "fixed", "title": "...", "description": "..." },
  ...
]
Regras:
- "new" = funcionalidades novas
- "improved" = melhorias em coisas existentes
- "fixed" = correções de bugs
- title: curto e direto (máx 60 chars)
- description: explicativo mas conciso (máx 120 chars)
- Gere quantos itens fizerem sentido com base na descrição
- Responda SOMENTE o array JSON, nada mais`;

      const apiUrl = process.env.NEXT_PUBLIC_CYM_API_URL;
      const apiKey = process.env.NEXT_PUBLIC_CYM_API_KEY;

      let rawReply = "";

      if (apiUrl && apiKey) {
        // Usa a API CYM diretamente
        const res = await fetch(`${apiUrl}/api/ai/generate`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": apiKey,
          },
          body: JSON.stringify({
            model: "CyM Pro",
            messages: [
              { role: "system", content: systemPrompt },
              { role: "user", content: prompt },
            ],
          }),
        });
        if (!res.ok) throw new Error(`CYM API error ${res.status}`);
        const data = await res.json();
        rawReply = typeof data.reply === "string" ? data.reply : JSON.stringify(data.reply ?? "");
      } else {
        // Fallback: rota interna /api/chatbot
        const res = await fetch("/api/chatbot", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: [
              { role: "system", content: systemPrompt },
              { role: "user", content: prompt },
            ],
          }),
        });
        if (!res.ok) throw new Error(`Chatbot error ${res.status}`);
        const data = await res.json();
        rawReply = typeof data.reply === "string" ? data.reply : "";
      }

      // Limpa possíveis blocos de código que a IA pode retornar
      const clean = rawReply
        .replace(/```json[\s\S]*?```/gi, (m) => m.replace(/```json|```/gi, ""))
        .replace(/```[\s\S]*?```/gi, (m) => m.replace(/```/gi, ""))
        .trim();

      const parsed: ChangelogItem[] = JSON.parse(clean);
      if (!Array.isArray(parsed)) throw new Error("Resposta inválida da IA");

      const valid = parsed.filter(
        (i) =>
          ["new", "improved", "fixed"].includes(i.type) &&
          typeof i.title === "string" &&
          typeof i.description === "string"
      );
      if (valid.length === 0) throw new Error("Nenhum item gerado");

      onApply(valid);
      onClose();
    } catch (e: any) {
      setError(e?.message ?? "Erro ao gerar com IA");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
        onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0, y: 10 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 10 }}
          transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-lg bg-background border border-foreground/12 rounded-2xl shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center gap-3 px-5 py-4 border-b border-foreground/8">
            <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold">Gerar Changelog com IA</p>
              <p className="text-[11px] text-foreground/38">Descreva o que foi feito e a IA monta os itens</p>
            </div>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-foreground/8 text-foreground/40 hover:text-foreground transition-all">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body */}
          <div className="p-5 space-y-4">
            <div>
              <label className="text-[11px] text-foreground/40 mb-1.5 block font-medium">
                Descreva o que mudou nessa atualização
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleGenerate(); }}
                placeholder="Ex: Adicionamos sistema de pagamentos com Stripe, corrigimos bug no login com Google, e melhoramos a velocidade do dashboard..."
                rows={5}
                className="w-full px-3 py-2.5 bg-background/50 border border-foreground/10 rounded-xl text-sm focus:outline-none focus:ring-1 focus:ring-primary transition-all resize-none placeholder:text-foreground/20"
                autoFocus
              />
              <p className="text-[10px] text-foreground/25 mt-1">Ctrl+Enter para gerar</p>
            </div>

            {error && (
              <div className="flex items-center gap-2 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-xs">
                <XCircle className="w-3.5 h-3.5 flex-shrink-0" />
                {error}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-foreground/8 bg-foreground/[0.015]">
            <button onClick={onClose} className="px-4 py-2 text-sm text-foreground/50 hover:text-foreground transition-colors">
              Cancelar
            </button>
            <button
              onClick={handleGenerate}
              disabled={loading || !prompt.trim()}
              className="flex items-center gap-2 px-5 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-primary/20"
            >
              {loading ? (
                <><RefreshCw className="w-4 h-4 animate-spin" /> Gerando...</>
              ) : (
                <><Sparkles className="w-4 h-4" /> Gerar Itens</>
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

// ── Editor ────────────────────────────────────────────────────────────────────

function ChangelogEditor({ id, onBack, onCreated }: { id: string | null; onBack: () => void; onCreated?: (newId: string) => void }) {
  const isNew = !id;
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [sendingWebhook, setSendingWebhook] = useState(false);
  const [togglingPublish, setTogglingPublish] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const [aiModalOpen, setAiModalOpen] = useState(false);

  const [version, setVersion] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [items, setItems] = useState<ChangelogItem[]>([]);
  const [published, setPublished] = useState(false);
  const [cfg, setCfg] = useState<WebhookConfig>({
    webhookUrl: "", coverImageUrl: "",
    accentColorMain: 0xc400c4, accentColorPromo: 0xa61fe3,
    promoText: "", promoButtonLabel: "Adquirir Pro",
    promoButtonUrl: "https://amethysapp.vercel.app/pricing",
    emojiNew: "🆕", emojiImproved: "⬆️", emojiFixed: "🔧",
    sentAt: null,
  });

  const showToast = (type: "success" | "error", msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3500);
  };

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch(`/api/admin/changelogs/${id}`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) return;
        const d: Changelog = data.data;
        setVersion(d.version ?? "");
        setTitle(d.title ?? "");
        setDescription(d.description ?? "");
        setItems(d.items ?? []);
        setPublished(d.published ?? false);
        if (d.webhookConfig) setCfg((p) => ({ ...p, ...d.webhookConfig }));
      })
      .catch(() => showToast("error", "Erro ao carregar"))
      .finally(() => setLoading(false));
  }, [id]);

  const handleSave = async () => {
    if (!version.trim() || !title.trim()) { showToast("error", "Versão e título são obrigatórios"); return; }
    setSaving(true);
    try {
      const res = await fetch(id ? `/api/admin/changelogs/${id}` : "/api/admin/changelogs", {
        method: id ? "PUT" : "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: version.trim(), title: title.trim(), description: description.trim(), items, webhookConfig: cfg }),
      });
      const data = await res.json();
      if (data.success) {
        showToast("success", id ? "Salvo!" : "Criado! Você já pode continuar editando.");
        if (!id && data.data?._id) { onCreated?.(data.data._id); }
      }
      else showToast("error", data.message || "Erro ao salvar");
    } catch { showToast("error", "Erro de conexão"); }
    finally { setSaving(false); }
  };

  const handleTogglePublish = async () => {
    if (!id) { showToast("error", "Salve antes de publicar"); return; }
    setTogglingPublish(true);
    try {
      const res = await fetch(`/api/admin/changelogs/${id}/publish`, { method: "POST", credentials: "include" });
      const data = await res.json();
      if (data.success) { setPublished(data.data.published); showToast("success", data.data.published ? "Publicado!" : "Despublicado!"); }
    } catch { showToast("error", "Erro"); }
    finally { setTogglingPublish(false); }
  };

  const handleSendWebhook = async () => {
    if (!id) { showToast("error", "Salve antes de enviar"); return; }
    if (!cfg.webhookUrl?.trim()) { showToast("error", "Configure a URL do webhook"); return; }
    setSendingWebhook(true);
    try {
      const res = await fetch(`/api/admin/changelogs/${id}/webhook`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
      });
      const data = await res.json();
      if (data.success) { showToast("success", "Enviado para o Discord! ✓"); setCfg((p) => ({ ...p, sentAt: new Date().toISOString() })); }
      else showToast("error", data.message || "Erro ao enviar");
    } catch { showToast("error", "Erro de conexão"); }
    finally { setSendingWebhook(false); }
  };

  const addItem = () => setItems((p) => [...p, { type: "new", title: "", description: "" }]);
  const updateItem = (i: number, it: ChangelogItem) => setItems((p) => p.map((x, idx) => (idx === i ? it : x)));
  const deleteItem = (i: number) => setItems((p) => p.filter((_, idx) => idx !== i));
  const moveItem = (i: number, dir: -1 | 1) => setItems((p) => { const a = [...p]; const ni = i + dir; if (ni < 0 || ni >= a.length) return a; [a[i], a[ni]] = [a[ni], a[i]]; return a; });
  const updateCfg = (k: keyof WebhookConfig, v: any) => setCfg((p) => ({ ...p, [k]: v }));

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <RefreshCw className="w-5 h-5 animate-spin text-primary" />
    </div>
  );

  const newCount = items.filter((x) => x.type === "new").length;
  const improvedCount = items.filter((x) => x.type === "improved").length;
  const fixedCount = items.filter((x) => x.type === "fixed").length;

  return (
    <>
      <Toast toast={toast} />

      {aiModalOpen && (
        <AIGenerateModal
          onClose={() => setAiModalOpen(false)}
          onApply={(generated) => setItems((prev) => [...prev, ...generated])}
        />
      )}

      {/* Header */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <button onClick={onBack} className="flex items-center gap-1.5 text-foreground/45 hover:text-foreground text-sm transition-colors">
          <ChevronLeft className="w-4 h-4" /> Voltar
        </button>
        <div className="w-px h-4 bg-foreground/12" />
        <h2 className="text-xl font-bold">{isNew ? "Novo Changelog" : `Editar ${version || "changelog"}`}</h2>
        {!isNew && (
          <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
            published ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-foreground/5 text-foreground/35 border-foreground/10"
          }`}>
            {published ? "● Publicado" : "○ Rascunho"}
          </span>
        )}
        {cfg.sentAt && (
          <span className="ml-auto text-[11px] text-[#7289da] font-mono">
            Discord ✓ {new Date(cfg.sentAt).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_370px] gap-6">
        {/* Left */}
        <div className="space-y-5 min-w-0">
          {/* Basic info */}
          <div className="bg-background/50 border border-foreground/10 rounded-xl p-5 space-y-4">
            <p className="text-[11px] font-semibold text-foreground/40 uppercase tracking-widest">Informações</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] text-foreground/40 mb-1.5 block">Versão *</label>
                <input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="v2.5.0"
                  className="w-full px-3 py-2.5 bg-background/50 border border-foreground/10 rounded-lg text-sm font-mono focus:outline-none focus:ring-1 focus:ring-primary transition-all placeholder:text-foreground/18" />
              </div>
              <div>
                <label className="text-[11px] text-foreground/40 mb-1.5 block">Título *</label>
                <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Nome da atualização"
                  className="w-full px-3 py-2.5 bg-background/50 border border-foreground/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary transition-all placeholder:text-foreground/18" />
              </div>
            </div>
            <div>
              <label className="text-[11px] text-foreground/40 mb-1.5 block">Descrição curta</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)}
                placeholder="Resumo do que mudou..." rows={2}
                className="w-full px-3 py-2.5 bg-background/50 border border-foreground/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary transition-all resize-none placeholder:text-foreground/18" />
            </div>
          </div>

          {/* Items */}
          <div className="bg-background/50 border border-foreground/10 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <p className="text-[11px] font-semibold text-foreground/40 uppercase tracking-widest">Itens</p>
                {/* Legend pills */}
                {newCount > 0 && <TypePill type="new" />}
                {improvedCount > 0 && <TypePill type="improved" />}
                {fixedCount > 0 && <TypePill type="fixed" />}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setAiModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/8 text-primary/80 border border-primary/15 rounded-lg text-xs font-medium hover:bg-primary/15 hover:text-primary transition-all"
                >
                  <Sparkles className="w-3.5 h-3.5" /> Gerar com IA
                </button>
                <button onClick={addItem}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 text-primary border border-primary/20 rounded-lg text-xs font-medium hover:bg-primary/20 transition-all">
                  <Plus className="w-3.5 h-3.5" /> Adicionar
                </button>
              </div>
            </div>

            <div className="space-y-3">
              <AnimatePresence>
                {items.length === 0 && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="text-center py-10 text-foreground/22 text-sm border border-dashed border-foreground/8 rounded-xl">
                    Clique em "Adicionar" para criar o primeiro item.
                  </motion.div>
                )}
                {items.map((item, i) => (
                  <ItemRow key={i} item={item} index={i} total={items.length}
                    onChange={(it) => updateItem(i, it)}
                    onDelete={() => deleteItem(i)}
                    onMove={(dir) => moveItem(i, dir)}
                  />
                ))}
              </AnimatePresence>
            </div>
          </div>

          {/* Webhook config */}
          <Collapsible
            title="Webhook Discord"
            icon={Settings}
            badge={cfg.sentAt ? (
              <span className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium">Enviado ✓</span>
            ) : null}
          >
            <div>
              <label className="text-[11px] text-foreground/40 mb-1.5 block">URL do Webhook *</label>
              <input value={cfg.webhookUrl || ""} onChange={(e) => updateCfg("webhookUrl", e.target.value)}
                placeholder="Cole a URL do webhook"
                className="w-full px-3 py-2 bg-background/50 border border-foreground/10 rounded-lg text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary transition-all placeholder:text-foreground/18" />
            </div>
            <div>
              <label className="text-[11px] text-foreground/40 mb-1.5 block">URL da Imagem de Capa</label>
              <input value={cfg.coverImageUrl || ""} onChange={(e) => updateCfg("coverImageUrl", e.target.value)}
                placeholder="https://i.imgur.com/..."
                className="w-full px-3 py-2 bg-background/50 border border-foreground/10 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-primary transition-all placeholder:text-foreground/18" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              {([
                { k: "accentColorMain" as keyof WebhookConfig, label: "Cor Principal", def: 0xc400c4 },
                { k: "accentColorPromo" as keyof WebhookConfig, label: "Cor do Promo", def: 0xa61fe3 },
              ] as const).map(({ k, label, def }) => (
                <div key={k}>
                  <label className="text-[11px] text-foreground/40 mb-1.5 block">{label}</label>
                  <div className="flex items-center gap-2">
                    <input type="color" value={numToHex((cfg[k] as number) ?? def)}
                      onChange={(e) => updateCfg(k, hexToNum(e.target.value))}
                      className="w-8 h-8 rounded-md border border-foreground/12 cursor-pointer bg-transparent p-0.5" />
                    <input value={numToHex((cfg[k] as number) ?? def)}
                      onChange={(e) => updateCfg(k, hexToNum(e.target.value))}
                      className="flex-1 px-2.5 py-1.5 bg-background/50 border border-foreground/10 rounded-lg text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary" />
                  </div>
                </div>
              ))}
            </div>

            {/* Emoji fields */}
            <div>
              <p className="text-[11px] text-foreground/35 mb-2 font-semibold uppercase tracking-wide">
                Emojis no Discord (unicode ou &lt;:name:id&gt;)
              </p>
              <div className="grid grid-cols-3 gap-3">
                {([
                  { k: "emojiNew" as keyof WebhookConfig, label: "Novo" },
                  { k: "emojiImproved" as keyof WebhookConfig, label: "Melhorado" },
                  { k: "emojiFixed" as keyof WebhookConfig, label: "Corrigido" },
                ] as const).map(({ k, label }) => (
                  <div key={k}>
                    <label className="text-[10px] text-foreground/35 mb-1 block">{label}</label>
                    <input value={(cfg[k] as string) || ""}
                      onChange={(e) => updateCfg(k, e.target.value)}
                      className="w-full px-2.5 py-2 bg-background/50 border border-foreground/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary" />
                  </div>
                ))}
              </div>
            </div>

            {/* Promo */}
            <div className="pt-3 border-t border-foreground/8 space-y-3">
              <p className="text-[11px] text-foreground/35 font-semibold uppercase tracking-wide">Container Promocional</p>
              <input value={cfg.promoText || ""} onChange={(e) => updateCfg("promoText", e.target.value)}
                placeholder="Texto do container promo..."
                className="w-full px-3 py-2 bg-background/50 border border-foreground/10 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-foreground/18" />
              <div className="grid grid-cols-2 gap-3">
                <input value={cfg.promoButtonLabel || ""} onChange={(e) => updateCfg("promoButtonLabel", e.target.value)}
                  placeholder="Label do botão"
                  className="w-full px-3 py-2 bg-background/50 border border-foreground/10 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-primary" />
                <input value={cfg.promoButtonUrl || ""} onChange={(e) => updateCfg("promoButtonUrl", e.target.value)}
                  placeholder="https://..."
                  className="w-full px-3 py-2 bg-background/50 border border-foreground/10 rounded-lg text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary" />
              </div>
            </div>
          </Collapsible>

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-3 pt-1 pb-8">
            <button onClick={handleSave} disabled={saving}
              className="flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-primary/20">
              {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
              {saving ? "Salvando..." : isNew ? "Criar" : "Salvar"}
            </button>

            {!isNew && (
              <>
                <button onClick={handleTogglePublish} disabled={togglingPublish}
                  className={`flex items-center gap-2 px-4 py-2.5 font-semibold rounded-xl text-sm transition-all border disabled:opacity-60 ${
                    published
                      ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20 hover:bg-yellow-500/18"
                      : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/18"
                  }`}>
                  {togglingPublish ? <RefreshCw className="w-4 h-4 animate-spin" /> : published ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  {published ? "Despublicar" : "Publicar"}
                </button>

                <button onClick={handleSendWebhook} disabled={sendingWebhook}
                  className="flex items-center gap-2 px-4 py-2.5 bg-[#5865F2]/10 text-[#7289da] border border-[#5865F2]/25 hover:bg-[#5865F2]/18 font-semibold rounded-xl text-sm transition-all disabled:opacity-60">
                  {sendingWebhook ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  {sendingWebhook ? "Enviando..." : "Enviar Discord"}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Right: preview */}
        <div>
          <div className="bg-background/50 border border-foreground/10 rounded-xl p-5 sticky top-24">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 rounded-full bg-[#5865F2]" />
              <p className="text-sm font-semibold">Preview Discord</p>
              <span className="ml-auto text-[10px] text-foreground/25 font-mono">Components V2</span>
            </div>
            <DiscordPreview description={description} items={items} cfg={cfg} />
          </div>
        </div>
      </div>
    </>
  );
}

// ── List ──────────────────────────────────────────────────────────────────────

function ChangelogsList({ onNew, onEdit }: { onNew: () => void; onEdit: (id: string) => void }) {
  const [changelogs, setChangelogs] = useState<Changelog[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const showToast = (type: "success" | "error", msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3000);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/changelogs", { credentials: "include" });
      const data = await res.json();
      if (data.success) setChangelogs(data.data);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    if (!confirm("Deletar este changelog?")) return;
    setDeleting(id);
    try {
      await fetch(`/api/admin/changelogs/${id}`, { method: "DELETE", credentials: "include" });
      setChangelogs((p) => p.filter((c) => c._id !== id));
      showToast("success", "Deletado!");
    } finally { setDeleting(null); }
  };

  const handleToggle = async (id: string) => {
    setToggling(id);
    try {
      const res = await fetch(`/api/admin/changelogs/${id}/publish`, { method: "POST", credentials: "include" });
      const data = await res.json();
      if (data.success) {
        setChangelogs((p) => p.map((c) => c._id === id ? { ...c, published: data.data.published } : c));
        showToast("success", data.data.published ? "Publicado!" : "Despublicado!");
      }
    } finally { setToggling(null); }
  };

  return (
    <>
      <Toast toast={toast} />
      <div className="space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">Changelogs</h2>
            <p className="text-foreground/38 text-sm mt-0.5">Notas de atualização públicas do Amethys.</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={load} className="p-2 rounded-lg border border-foreground/10 hover:bg-foreground/5 text-foreground/45 hover:text-foreground transition-all">
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button onClick={onNew}
              className="flex items-center gap-2 px-4 py-2.5 bg-primary hover:bg-primary/90 text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-primary/20">
              <Plus className="w-4 h-4" /> Novo Changelog
            </button>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-5 h-5 animate-spin text-primary" />
          </div>
        )}

        {!loading && changelogs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 border border-dashed border-foreground/8 rounded-2xl gap-3">
            <FileText className="w-10 h-10 text-foreground/12" />
            <p className="text-foreground/28 text-sm">Nenhum changelog criado.</p>
            <button onClick={onNew}
              className="px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-xl text-sm font-medium hover:bg-primary/18 transition-all">
              Criar primeiro
            </button>
          </div>
        )}

        <div className="space-y-3">
          {changelogs.map((cl, i) => {
            const n = cl.items.filter((x) => x.type === "new").length;
            const im = cl.items.filter((x) => x.type === "improved").length;
            const f = cl.items.filter((x) => x.type === "fixed").length;

            return (
              <motion.div key={cl._id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="bg-background/50 border border-foreground/8 hover:border-foreground/16 rounded-xl p-4 transition-all group"
              >
                <div className="flex items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="text-xs font-black font-mono text-primary bg-primary/10 border border-primary/20 px-2.5 py-1 rounded-lg">
                        {cl.version}
                      </span>
                      <span className="font-semibold text-sm truncate">{cl.title}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${
                        cl.published ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/18" : "text-foreground/28 bg-foreground/5 border-foreground/8"
                      }`}>
                        {cl.published ? "● Publicado" : "○ Rascunho"}
                      </span>
                      {cl.webhookConfig?.sentAt && (
                        <span className="text-[10px] text-[#7289da] bg-[#5865F2]/10 border border-[#5865F2]/18 px-2 py-0.5 rounded-full font-semibold">
                          Discord ✓
                        </span>
                      )}
                    </div>

                    {cl.description && (
                      <p className="text-foreground/38 text-xs mt-1.5 line-clamp-1">{cl.description}</p>
                    )}

                    {/* Type pills */}
                    <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
                      {n > 0 && <TypePill type="new" />}
                      {im > 0 && <TypePill type="improved" />}
                      {f > 0 && <TypePill type="fixed" />}
                      <span className="text-foreground/20 text-[10px] font-mono ml-auto">
                        {new Date(cl.createdAt).toLocaleDateString("pt-BR")}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 shrink-0">
                    <button onClick={() => handleToggle(cl._id)} disabled={toggling === cl._id}
                      className={`p-2 rounded-lg border transition-all disabled:opacity-50 ${
                        cl.published
                          ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/18 hover:bg-emerald-500/18"
                          : "text-foreground/35 border-foreground/8 hover:text-foreground hover:bg-foreground/8"
                      }`}>
                      {toggling === cl._id ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : cl.published ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                    </button>
                    <button onClick={() => onEdit(cl._id)}
                      className="p-2 rounded-lg border border-foreground/8 text-foreground/35 hover:text-foreground hover:bg-foreground/8 transition-all">
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={() => handleDelete(cl._id)} disabled={deleting === cl._id}
                      className="p-2 rounded-lg border border-foreground/8 text-foreground/28 hover:text-red-400 hover:bg-red-500/10 hover:border-red-500/18 transition-all disabled:opacity-50">
                      {deleting === cl._id ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </>
  );
}

// ── Export ────────────────────────────────────────────────────────────────────

export function ChangelogsSection() {
  const [view, setView] = useState<"list" | "edit">("list");
  const [editId, setEditId] = useState<string | null>(null);

  if (view === "edit") {
    return (
      <ChangelogEditor
        id={editId}
        onBack={() => setView("list")}
        onCreated={(newId) => setEditId(newId)}
      />
    );
  }

  return (
    <ChangelogsList
      onNew={() => { setEditId(null); setView("edit"); }}
      onEdit={(id) => { setEditId(id); setView("edit"); }}
    />
  );
}
