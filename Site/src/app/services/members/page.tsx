"use client";

/**
 * src/app/services/members/page.tsx
 *
 * Página de compra de Members para servidores Discord.
 * - Obriga login para comprar
 * - Seleção de tipo (online / offline)
 * - Seleção de quantidade com slider + input
 * - Verificação de link do servidor
 * - Geração de PIX Mistic
 * - Polling de status + tela de aprovação
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button, Chip, Progress, Spinner } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faUsers,
  faWifi,
  faUserSecret,
  faLink,
  faMinus,
  faPlus,
  faTag,
  faCopy,
  faCheck,
  faCircleCheck,
  faTriangleExclamation,
  faArrowRight,
  faReceipt,
  faLock,
  faShield,
  faBolt,
} from "@fortawesome/free-solid-svg-icons";
import { faDiscord } from "@fortawesome/free-brands-svg-icons";
import { useRouter } from "next/navigation";

// ─── Types ────────────────────────────────────────────────────────────────────

type MemberType = "online" | "offline";

interface Service {
  id: string;
  name: string;
  type: MemberType;
  description: string;
  pricePerUnit: number;
  minQty: number;
  maxQty: number;
}

interface BreakdownPreview {
  servicePrice: number;
  ourFee: number;
  misticFee: number;
  total: number;
}

interface PixPayment {
  misticId: string;
  emv: string;
  qrCodeBase64: string;
  expiresAt: string;
  total: number;
}

interface CreatedOrder {
  _id: string;
  status: string;
  serviceName: string;
  quantity: number;
  serverLink: string;
  breakdown: BreakdownPreview;
}

type Step = "select" | "configure" | "payment" | "done";

const OUR_FEE = 1.5;
const MISTIC_FEE = 0.5;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function calcTotal(pricePerUnit: number, qty: number): BreakdownPreview {
  const servicePrice = parseFloat((pricePerUnit * qty).toFixed(2));
  const total = parseFloat((servicePrice + OUR_FEE + MISTIC_FEE).toFixed(2));
  return { servicePrice, ourFee: OUR_FEE, misticFee: MISTIC_FEE, total };
}

function fmtBRL(value: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

// ─── Step indicators ─────────────────────────────────────────────────────────

const STEPS: { key: Step; label: string }[] = [
  { key: "select", label: "Tipo" },
  { key: "configure", label: "Configurar" },
  { key: "payment", label: "Pagamento" },
  { key: "done", label: "Concluído" },
];

function StepBar({ current }: { current: Step }) {
  const idx = STEPS.findIndex((s) => s.key === current);
  return (
    <div className="flex items-center gap-0 w-full max-w-md mx-auto mb-10">
      {STEPS.map((s, i) => {
        const done = i < idx;
        const active = i === idx;
        return (
          <div key={s.key} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all duration-300 ${
                  done
                    ? "bg-primary border-primary text-white"
                    : active
                    ? "bg-primary/15 border-primary text-primary"
                    : "bg-foreground/5 border-foreground/15 text-foreground/30"
                }`}
              >
                {done ? <FontAwesomeIcon icon={faCheck} className="text-[10px]" /> : i + 1}
              </div>
              <span
                className={`text-[10px] font-semibold whitespace-nowrap ${
                  active ? "text-primary" : done ? "text-foreground/50" : "text-foreground/25"
                }`}
              >
                {s.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={`flex-1 h-px mx-2 mb-4 transition-all duration-500 ${
                  done ? "bg-primary" : "bg-foreground/10"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Type card ────────────────────────────────────────────────────────────────

function TypeCard({
  type,
  selected,
  onSelect,
}: {
  type: MemberType;
  selected: boolean;
  onSelect: () => void;
}) {
  const isOnline = type === "online";
  return (
    <motion.button
      onClick={onSelect}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`relative flex flex-col gap-4 p-6 rounded-2xl border-2 text-left w-full transition-all duration-200 overflow-hidden ${
        selected
          ? isOnline
            ? "border-emerald-500/60 bg-emerald-500/[0.07]"
            : "border-primary/60 bg-primary/[0.07]"
          : "border-foreground/10 bg-foreground/[0.02] hover:border-foreground/25"
      }`}
    >
      {/* Glow bg */}
      {selected && (
        <div
          className={`absolute inset-0 pointer-events-none blur-3xl opacity-20 ${
            isOnline ? "bg-emerald-400" : "bg-primary"
          }`}
        />
      )}

      <div
        className={`w-12 h-12 rounded-xl flex items-center justify-center border text-xl ${
          selected
            ? isOnline
              ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
              : "bg-primary/15 border-primary/30 text-primary"
            : "bg-foreground/5 border-foreground/10 text-foreground/40"
        }`}
      >
        <FontAwesomeIcon icon={isOnline ? faWifi : faUserSecret} />
      </div>

      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="font-bold text-base">
            {isOnline ? "Members Online" : "Members Offline"}
          </span>
          {selected && (
            <span
              className={`text-[10px] font-black px-2 py-0.5 rounded-full ${
                isOnline
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "bg-primary/20 text-primary"
              }`}
            >
              SELECIONADO
            </span>
          )}
        </div>
        <p className="text-xs text-foreground/50 leading-relaxed">
          {isOnline
            ? "Membros que aparecem online no servidor. Maior impacto visual imediato."
            : "Membros que aparecem offline. Mais naturais e discretos para o servidor."}
        </p>
      </div>

      <div className="flex items-center gap-1.5">
        <div
          className={`w-2 h-2 rounded-full ${isOnline ? "bg-emerald-400 animate-pulse" : "bg-foreground/30"}`}
        />
        <span className={`text-xs font-medium ${isOnline ? "text-emerald-400" : "text-foreground/40"}`}>
          {isOnline ? "Status Online" : "Status Offline"}
        </span>
      </div>
    </motion.button>
  );
}

// ─── Quantity selector ────────────────────────────────────────────────────────

function QtySelector({
  value,
  min,
  max,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  const clamp = (v: number) => Math.max(min, Math.min(max, v));

  return (
    <div className="flex flex-col gap-3">
      {/* Controls */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => onChange(clamp(value - 100))}
          className="w-9 h-9 rounded-xl bg-foreground/8 border border-foreground/10 flex items-center justify-center text-foreground/70 hover:bg-foreground/15 transition-colors"
        >
          <FontAwesomeIcon icon={faMinus} className="text-xs" />
        </button>
        <input
          type="number"
          value={value}
          min={min}
          max={max}
          onChange={(e) => onChange(clamp(Number(e.target.value) || min))}
          className="flex-1 text-center text-2xl font-black bg-foreground/5 border border-foreground/10 rounded-xl py-2.5 focus:outline-none focus:border-primary/50 focus:bg-primary/5 transition-all"
        />
        <button
          onClick={() => onChange(clamp(value + 100))}
          className="w-9 h-9 rounded-xl bg-foreground/8 border border-foreground/10 flex items-center justify-center text-foreground/70 hover:bg-foreground/15 transition-colors"
        >
          <FontAwesomeIcon icon={faPlus} className="text-xs" />
        </button>
      </div>

      {/* Slider */}
      <input
        type="range"
        min={min}
        max={max}
        step={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-primary cursor-pointer"
      />

      {/* Quick pick */}
      <div className="flex gap-2 flex-wrap">
        {[500, 1000, 2500, 5000].filter((v) => v >= min && v <= max).map((v) => (
          <button
            key={v}
            onClick={() => onChange(v)}
            className={`px-3 py-1 rounded-lg text-xs font-semibold border transition-all ${
              value === v
                ? "bg-primary/15 border-primary/40 text-primary"
                : "bg-foreground/5 border-foreground/10 text-foreground/50 hover:border-foreground/25"
            }`}
          >
            {v.toLocaleString("pt-BR")}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Breakdown card ───────────────────────────────────────────────────────────

function BreakdownCard({ bd, qty, service }: { bd: BreakdownPreview; qty: number; service: Service }) {
  return (
    <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.025] p-5 flex flex-col gap-3">
      <div className="flex items-center gap-2 mb-1">
        <FontAwesomeIcon icon={faReceipt} className="text-primary text-sm" />
        <span className="text-sm font-bold">Resumo do pedido</span>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex justify-between text-foreground/60">
          <span>
            {qty.toLocaleString("pt-BR")}x {service.name}
          </span>
          <span>{fmtBRL(bd.servicePrice)}</span>
        </div>
        <div className="flex justify-between text-foreground/50 text-xs">
          <span>Taxa de serviço</span>
          <span>{fmtBRL(bd.ourFee)}</span>
        </div>
        <div className="flex justify-between text-foreground/50 text-xs">
          <span>Taxa de processamento</span>
          <span>{fmtBRL(bd.misticFee)}</span>
        </div>
        <div className="h-px bg-foreground/10" />
        <div className="flex justify-between font-black text-base">
          <span>Total</span>
          <span className="text-primary">{fmtBRL(bd.total)}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 text-[11px] text-foreground/35 mt-1">
        <FontAwesomeIcon icon={faShield} />
        <span>Pagamento 100% seguro via PIX</span>
      </div>
    </div>
  );
}

// ─── Pix payment view ─────────────────────────────────────────────────────────

function PixView({
  payment,
  onDone,
}: {
  payment: PixPayment;
  orderId: string;
  onDone: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const iv = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    const expires = new Date(payment.expiresAt).getTime();
    setTimeLeft(Math.max(0, Math.floor((expires - now) / 1000)));
  }, [payment.expiresAt, now]);

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;
  const progress = Math.round((timeLeft / (30 * 60)) * 100);

  const imgSrc = useMemo(() => {
    const s = payment.qrCodeBase64 || "";
    if (!s) return null;
    return s.startsWith("data:") ? s : `data:image/png;base64,${s}`;
  }, [payment.qrCodeBase64]);

  const copyCode = () => {
    navigator.clipboard.writeText(payment.emv);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-5"
    >
      {/* Timer */}
      <div className="flex items-center justify-between bg-foreground/5 border border-foreground/10 rounded-xl px-4 py-3">
        <span className="text-sm text-foreground/60">Expira em</span>
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-lg text-primary">
            {minutes.toString().padStart(2, "0")}:{seconds.toString().padStart(2, "0")}
          </span>
        </div>
      </div>
      <Progress
        value={progress}
        color="primary"
        aria-label="Tempo restante"
        className="h-1.5"
      />

      {/* QR + Steps */}
      <div className="flex flex-col md:flex-row gap-6 items-start">
        {imgSrc && (
          <div className="self-center md:self-start bg-white p-3 rounded-2xl shadow-xl shrink-0">
            <img src={imgSrc} alt="QR Code PIX" className="w-48 h-48 rounded-lg" />
          </div>
        )}

        <div className="flex flex-col gap-4 flex-1">
          {[
            { n: 1, title: "Abra seu banco", desc: "Acesse o aplicativo do seu banco ou carteira digital." },
            { n: 2, title: "Escaneie ou use copia e cola", desc: "Aponte a câmera para o QR Code ou use o código abaixo." },
            { n: 3, title: "Confirme o pagamento", desc: "Verifique o valor e finalize. A entrega é automática!" },
          ].map((step) => (
            <div key={step.n} className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-primary/15 border border-primary/25 text-primary text-xs font-bold flex items-center justify-center shrink-0">
                {step.n}
              </div>
              <div>
                <p className="text-sm font-semibold">{step.title}</p>
                <p className="text-xs text-foreground/50 leading-relaxed">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Copy code */}
      <div>
        <p className="text-xs text-foreground/50 mb-2 font-medium">PIX Copia e Cola</p>
        <div className="flex items-center gap-2">
          <code className="flex-1 text-[11px] font-mono bg-foreground/5 border border-foreground/10 rounded-xl px-4 py-3 truncate text-foreground/60">
            {payment.emv}
          </code>
          <button
            onClick={copyCode}
            className="w-11 h-11 flex items-center justify-center rounded-xl bg-primary/10 border border-primary/25 text-primary hover:bg-primary/20 transition-all shrink-0"
          >
            <FontAwesomeIcon icon={copied ? faCheck : faCopy} className="text-sm" />
          </button>
        </div>
      </div>

      {copied && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-2"
        >
          <FontAwesomeIcon icon={faCheck} />
          Código copiado! Cole no seu banco.
        </motion.div>
      )}

      <p className="text-xs text-foreground/35 text-center">
        Aguardando confirmação do pagamento…<br />A entrega começa automaticamente após a aprovação.
      </p>
    </motion.div>
  );
}

// ─── Login gate ───────────────────────────────────────────────────────────────

function LoginGate() {
  const router = useRouter();
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center gap-6 text-center py-16 px-4 max-w-sm mx-auto"
    >
      <div className="w-20 h-20 rounded-3xl bg-primary/10 border border-primary/20 flex items-center justify-center">
        <FontAwesomeIcon icon={faLock} className="text-primary text-3xl" />
      </div>
      <div>
        <h2 className="text-2xl font-black mb-2">Login obrigatório</h2>
        <p className="text-foreground/55 text-sm leading-relaxed">
          Para comprar members e acompanhar seus pedidos, você precisa estar logado.
        </p>
      </div>
      <div className="flex flex-col gap-2 w-full">
        <Button
          color="primary"
          fullWidth
          className="font-semibold"
          onPress={() => router.push("/login?redirect=/services/members")}
        >
          Fazer login
        </Button>
        <Button
          variant="flat"
          fullWidth
          className="font-semibold text-foreground/60"
          onPress={() => router.push("/register")}
        >
          Criar conta grátis
        </Button>
      </div>
    </motion.div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function MembersServicePage() {
  const router = useRouter();

  // Auth
  const [user, setUser] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Flow state
  const [step, setStep] = useState<Step>("select");
  const [memberType, setMemberType] = useState<MemberType>("online");
  const [services, setServices] = useState<Service[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [qty, setQty] = useState(500);
  const [serverLink, setServerLink] = useState("");
  const [linkError, setLinkError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Payment
  const [pixPayment, setPixPayment] = useState<PixPayment | null>(null);
  const [createdOrder, setCreatedOrder] = useState<CreatedOrder | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<"pending" | "approved" | "cancelled">("pending");
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Derived
  const selectedService = useMemo(
    () => services.find((s) => s.type === memberType) ?? null,
    [services, memberType]
  );

  const breakdown = useMemo(
    () => (selectedService ? calcTotal(selectedService.pricePerUnit, qty) : null),
    [selectedService, qty]
  );

  // ── Auth check ──────────────────────────────────────────────────────────────
  useEffect(() => {
    fetch("/api/auth/session", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setUser(d?.user ?? d?.data ?? null))
      .catch(() => setUser(null))
      .finally(() => setAuthLoading(false));
  }, []);

  // ── Load services ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!user) return;
    setServicesLoading(true);
    fetch("/api/members/services", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => {
        if (d.success) setServices(d.services ?? []);
      })
      .catch(() => {})
      .finally(() => setServicesLoading(false));
  }, [user]);

  // ── Sync qty to service limits ──────────────────────────────────────────────
  useEffect(() => {
    if (!selectedService) return;
    setQty((q) =>
      Math.max(selectedService.minQty, Math.min(selectedService.maxQty, q))
    );
  }, [selectedService]);

  // ── Poll payment status ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!createdOrder || !pixPayment || paymentStatus !== "pending") {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }

    let mounted = true;
    const poll = async () => {
      try {
        const r = await fetch(`/api/members/orders/${createdOrder._id}/status`, {
          credentials: "include",
          cache: "no-store",
        });
        const d = await r.json();
        if (!mounted) return;
        if (d.status === "payment_confirmed" || d.paymentStatus === "approved") {
          setPaymentStatus("approved");
          setStep("done");
        } else if (d.status === "cancelled") {
          setPaymentStatus("cancelled");
        }
      } catch {}
    };

    poll();
    pollRef.current = setInterval(poll, 5000);
    return () => {
      mounted = false;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [createdOrder, pixPayment, paymentStatus]);

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleCreateOrder = async () => {
    if (!selectedService || !serverLink.trim()) {
      setLinkError("Informe o link do servidor Discord.");
      return;
    }
    setLinkError(null);
    setCreateError(null);
    setCreating(true);

    try {
      const res = await fetch("/api/members/orders", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          serviceId: selectedService.id,
          quantity: qty,
          serverLink: serverLink.trim(),
        }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        if (data.needsBot) {
          setCreateError(
            `O bot não está no servidor! Adicione-o antes de continuar: ${data.botInviteUrl ?? ""}`
          );
        } else {
          setCreateError(data.error || "Erro ao criar pedido.");
        }
        return;
      }

      setCreatedOrder(data.order);
      setPixPayment(data.payment);
      setStep("payment");
    } catch (err: any) {
      setCreateError("Erro de conexão. Tente novamente.");
    } finally {
      setCreating(false);
    }
  };

  // ── Renders ─────────────────────────────────────────────────────────────────

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <main className="relative overflow-x-hidden">
      {/* ── Hero ── */}
      <section className="relative flex flex-col items-center justify-center text-center pt-20 pb-10 -mt-20 overflow-hidden">
        {/* Glows */}
        <div className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-[320px] rounded-full bg-primary/8 blur-[100px]" />
        <div className="pointer-events-none absolute top-10 left-1/4 w-[200px] h-[200px] rounded-full bg-emerald-500/5 blur-[80px]" />

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
          className="relative z-10 flex flex-col items-center gap-4 max-w-2xl mx-auto px-4"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/28 bg-primary/8 text-xs font-semibold text-primary"
          >
            <FontAwesomeIcon icon={faBolt} className="text-[10px]" />
            Serviços Discord
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.16, duration: 0.62 }}
            className="text-5xl sm:text-6xl md:text-7xl font-black leading-[0.93] tracking-tight"
          >
            <span className="text-primary">Members</span> para<br />seu servidor
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.28, duration: 0.5 }}
            className="text-foreground/45 text-sm md:text-base max-w-md leading-relaxed"
          >
            Aumente a contagem de membros do seu servidor com entrega rápida e automática.
            Escolha entre online ou offline, na quantidade que quiser.
          </motion.p>

          {/* Badges */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="flex flex-wrap items-center justify-center gap-2 mt-1"
          >
            {[
              { icon: faBolt, label: "Entrega automática" },
              { icon: faShield, label: "Pagamento seguro" },
              { icon: faDiscord, label: "Discord" },
            ].map((b) => (
              <span
                key={b.label}
                className="flex items-center gap-1.5 text-[11px] font-semibold text-foreground/40 bg-foreground/5 border border-foreground/8 px-3 py-1 rounded-full"
              >
                <FontAwesomeIcon icon={b.icon} className="text-[9px]" />
                {b.label}
              </span>
            ))}
          </motion.div>
        </motion.div>
      </section>

      {/* ── Content ── */}
      <section className="max-w-3xl mx-auto px-4 pb-24">
        {!user ? (
          <LoginGate />
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <StepBar current={step} />

            <AnimatePresence mode="wait">
              {/* ── STEP: select ── */}
              {step === "select" && (
                <motion.div
                  key="select"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                  className="flex flex-col gap-6"
                >
                  <div>
                    <h2 className="text-2xl font-black mb-1">Escolha o tipo de member</h2>
                    <p className="text-foreground/50 text-sm">
                      Selecione o perfil de membro que deseja adicionar ao seu servidor.
                    </p>
                  </div>

                  {servicesLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <Spinner />
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {(["online", "offline"] as MemberType[]).map((t) => (
                        <TypeCard
                          key={t}
                          type={t}
                          selected={memberType === t}
                          onSelect={() => setMemberType(t)}
                        />
                      ))}
                    </div>
                  )}

                  {/* Info cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {[
                      { icon: faBolt, title: "Entrega rápida", desc: "Processo automático após confirmação do pagamento." },
                      { icon: faShield, title: "Seguro", desc: "Pagamento via PIX com confirmação instantânea." },
                      { icon: faUsers, title: "Volume", desc: "Centenas a milhares de membros de uma vez." },
                    ].map((card) => (
                      <div
                        key={card.title}
                        className="flex flex-col gap-2 p-4 rounded-xl border border-foreground/8 bg-foreground/[0.02]"
                      >
                        <FontAwesomeIcon icon={card.icon} className="text-primary text-sm" />
                        <p className="text-sm font-semibold">{card.title}</p>
                        <p className="text-xs text-foreground/45 leading-relaxed">{card.desc}</p>
                      </div>
                    ))}
                  </div>

                  <Button
                    color="primary"
                    size="lg"
                    className="font-bold w-full"
                    isDisabled={servicesLoading || !selectedService}
                    endContent={<FontAwesomeIcon icon={faArrowRight} />}
                    onPress={() => setStep("configure")}
                  >
                    Continuar com {memberType === "online" ? "Members Online" : "Members Offline"}
                  </Button>
                </motion.div>
              )}

              {/* ── STEP: configure ── */}
              {step === "configure" && (
                <motion.div
                  key="configure"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                  className="flex flex-col gap-6"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-2xl font-black mb-1">Configure seu pedido</h2>
                      <p className="text-foreground/50 text-sm">Defina a quantidade e o servidor de destino.</p>
                    </div>
                    <Chip
                      variant="flat"
                      color={memberType === "online" ? "success" : "default"}
                      startContent={
                        <FontAwesomeIcon
                          icon={memberType === "online" ? faWifi : faUserSecret}
                          className="text-[11px] ml-1"
                        />
                      }
                      className="text-xs font-semibold"
                    >
                      {memberType === "online" ? "Online" : "Offline"}
                    </Chip>
                  </div>

                  {/* Quantity */}
                  <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.025] p-5">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <p className="text-sm font-bold">Quantidade de members</p>
                        <p className="text-xs text-foreground/45 mt-0.5">
                          Mín. {selectedService?.minQty.toLocaleString("pt-BR")} — Máx.{" "}
                          {selectedService?.maxQty.toLocaleString("pt-BR")}
                        </p>
                      </div>
                      {selectedService && (
                        <span className="text-xs text-foreground/40 font-mono">
                          {fmtBRL(selectedService.pricePerUnit)}/un
                        </span>
                      )}
                    </div>

                    {selectedService && (
                      <QtySelector
                        value={qty}
                        min={selectedService.minQty}
                        max={selectedService.maxQty}
                        onChange={setQty}
                      />
                    )}
                  </div>

                  {/* Server link */}
                  <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.025] p-5 flex flex-col gap-3">
                    <div>
                      <p className="text-sm font-bold mb-0.5">Link do servidor Discord</p>
                      <p className="text-xs text-foreground/45">
                        Cole o link de convite ou o link do canal do seu servidor.
                      </p>
                    </div>

                    <div className="relative">
                      <FontAwesomeIcon
                        icon={faLink}
                        className="absolute left-3.5 top-1/2 -translate-y-1/2 text-foreground/30 text-sm"
                      />
                      <input
                        type="url"
                        placeholder="https://discord.gg/seuservidor"
                        value={serverLink}
                        onChange={(e) => {
                          setServerLink(e.target.value);
                          setLinkError(null);
                        }}
                        className={`w-full pl-10 pr-4 py-3 rounded-xl bg-foreground/5 border text-sm focus:outline-none transition-all ${
                          linkError
                            ? "border-red-500/50 focus:border-red-500/80"
                            : "border-foreground/10 focus:border-primary/50 focus:bg-primary/5"
                        }`}
                      />
                    </div>

                    {linkError && (
                      <motion.p
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-xs text-red-400 flex items-center gap-1.5"
                      >
                        <FontAwesomeIcon icon={faTriangleExclamation} />
                        {linkError}
                      </motion.p>
                    )}

                    {/* Bot notice */}
                    <div className="flex items-start gap-2 text-xs text-foreground/40 bg-foreground/5 border border-foreground/8 rounded-xl p-3 leading-relaxed">
                      <FontAwesomeIcon icon={faDiscord} className="mt-0.5 shrink-0" />
                      <span>
                        Certifique-se de que o bot está adicionado ao seu servidor antes de continuar.{" "}
                        <a
                          href="https://discord.com/oauth2/authorize?client_id=SEU_CLIENT_ID_AQUI&permissions=8&scope=bot"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary underline"
                        >
                          Adicionar bot
                        </a>
                      </span>
                    </div>
                  </div>

                  {/* Breakdown */}
                  {breakdown && selectedService && (
                    <BreakdownCard bd={breakdown} qty={qty} service={selectedService} />
                  )}

                  {/* Error */}
                  {createError && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-start gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl p-4"
                    >
                      <FontAwesomeIcon icon={faTriangleExclamation} className="mt-0.5 shrink-0" />
                      <span>{createError}</span>
                    </motion.div>
                  )}

                  <div className="flex gap-3">
                    <Button
                      variant="flat"
                      className="font-semibold"
                      onPress={() => setStep("select")}
                    >
                      Voltar
                    </Button>
                    <Button
                      color="primary"
                      size="lg"
                      className="font-bold flex-1"
                      isLoading={creating}
                      isDisabled={!selectedService || !serverLink.trim() || creating}
                      endContent={!creating && <FontAwesomeIcon icon={faArrowRight} />}
                      onPress={handleCreateOrder}
                    >
                      {creating ? "Gerando pedido…" : `Pagar ${breakdown ? fmtBRL(breakdown.total) : ""}`}
                    </Button>
                  </div>
                </motion.div>
              )}

              {/* ── STEP: payment ── */}
              {step === "payment" && pixPayment && createdOrder && (
                <motion.div
                  key="payment"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                  className="flex flex-col gap-6"
                >
                  <div>
                    <h2 className="text-2xl font-black mb-1">Finalize o pagamento</h2>
                    <p className="text-foreground/50 text-sm">
                      Pedido <span className="font-mono text-foreground/70">#{createdOrder._id.slice(-8)}</span>{" "}
                      criado. Realize o pagamento PIX para iniciar a entrega.
                    </p>
                  </div>

                  {/* Order summary strip */}
                  <div className="flex flex-wrap items-center gap-3 p-4 rounded-xl border border-foreground/8 bg-foreground/[0.02]">
                    <Chip
                      variant="flat"
                      color={memberType === "online" ? "success" : "default"}
                      size="sm"
                      className="text-xs"
                    >
                      {createdOrder.serviceName}
                    </Chip>
                    <span className="text-sm text-foreground/60">
                      {createdOrder.quantity.toLocaleString("pt-BR")} members
                    </span>
                    <span className="text-foreground/20">·</span>
                    <span className="text-sm font-bold text-primary">
                      {fmtBRL(createdOrder.breakdown.total)}
                    </span>
                  </div>

                  <PixView
                    payment={pixPayment}
                    orderId={createdOrder._id}
                    onDone={() => setStep("done")}
                  />
                </motion.div>
              )}

              {/* ── STEP: done ── */}
              {step === "done" && (
                <motion.div
                  key="done"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                  className="flex flex-col items-center gap-6 text-center py-8"
                >
                  {/* Success icon */}
                  <div className="relative">
                    <div className="w-24 h-24 rounded-3xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
                      <FontAwesomeIcon icon={faCircleCheck} className="text-emerald-400 text-4xl" />
                    </div>
                    <div className="absolute inset-0 blur-2xl bg-emerald-500/20 rounded-3xl -z-10" />
                  </div>

                  <div>
                    <h2 className="text-3xl font-black mb-2">Pagamento aprovado! 🎉</h2>
                    <p className="text-foreground/55 text-sm leading-relaxed max-w-sm mx-auto">
                      Seu pagamento foi confirmado. A entrega dos members no servidor está sendo processada automaticamente.
                    </p>
                  </div>

                  {createdOrder && (
                    <div className="w-full max-w-sm rounded-2xl border border-foreground/10 bg-foreground/[0.025] p-5 text-left flex flex-col gap-3">
                      <p className="text-xs font-bold text-foreground/40 uppercase tracking-wider">Resumo do pedido</p>
                      {[
                        { label: "Serviço", value: createdOrder.serviceName },
                        { label: "Quantidade", value: `${createdOrder.quantity.toLocaleString("pt-BR")} members` },
                        { label: "Servidor", value: createdOrder.serverLink },
                        { label: "Total pago", value: fmtBRL(createdOrder.breakdown.total) },
                      ].map((row) => (
                        <div key={row.label} className="flex justify-between text-sm">
                          <span className="text-foreground/50">{row.label}</span>
                          <span className="font-semibold truncate max-w-[55%] text-right">{row.value}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex flex-col gap-2 w-full max-w-sm">
                    <Button
                      color="primary"
                      fullWidth
                      className="font-bold"
                      onPress={() => router.push("/dashboard/invoices")}
                      endContent={<FontAwesomeIcon icon={faReceipt} />}
                    >
                      Ver em Faturas
                    </Button>
                    <Button
                      variant="flat"
                      fullWidth
                      className="font-semibold text-foreground/60"
                      onPress={() => {
                        setStep("select");
                        setServerLink("");
                        setPixPayment(null);
                        setCreatedOrder(null);
                        setPaymentStatus("pending");
                      }}
                    >
                      Fazer novo pedido
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </section>
    </main>
  );
}