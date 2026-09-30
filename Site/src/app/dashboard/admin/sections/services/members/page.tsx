"use client";

/**
 * src/app/dashboard/admin/services/members/page.tsx
 *
 * Painel admin completo para o serviço de Members:
 *  - Tab Configuração: cookie RevisionSMM, CPF, validar, saldo
 *  - Tab Serviços: CRUD dos serviços (online/offline, preços, min/max qty)
 *  - Tab Pedidos: listagem com filtros, retry, check revision
 *  - Tab Stats: receita, pedidos por status
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Button, Chip, Spinner } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faUsers,
  faGear,
  faListCheck,
  faChartBar,
  faArrowLeft,
  faKey,
  faWallet,
  faCircleCheck,
  faTriangleExclamation,
  faRotate,
  faPen,
  faTrash,
  faPlus,
  faEye,
  faFilter,
  faChevronLeft,
  faChevronRight,
  faSave,
  faXmark,
  faWifi,
  faUserSecret,
  faBolt,
} from "@fortawesome/free-solid-svg-icons";
import { useRequireAdmin } from "@/hooks/useAuth";
import { Loading } from "@/components/Loading";

// ─── Types ────────────────────────────────────────────────────────────────────

interface RevisionService {
  id: string;
  name: string;
  type: "online" | "offline";
  description?: string;
  pricePerUnit: number;
  minQty: number;
  maxQty: number;
}

interface MemberOrder {
  _id: string;
  status: string;
  serviceName: string;
  quantity: number;
  serverLink: string;
  guildId: string;
  totalCharged: number;
  servicePrice: number;
  ourFee: number;
  misticFee: number;
  payment: { status: string; misticId?: string; paidAt?: string };
  revision: { orderId?: string; orderStatus?: string; addFundsStatus?: string };
  userId?: { username?: string; email?: string };
  createdAt: string;
  failReason?: string;
  notes?: string;
}

type Tab = "config" | "services" | "orders" | "stats";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtBRL(v: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);
}

function fmtDate(d: string) {
  return new Date(d).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

const STATUS_CONFIG: Record<string, { label: string; color: "success" | "warning" | "danger" | "primary" | "default" | "secondary" }> = {
  awaiting_payment:  { label: "Aguard. pagamento", color: "warning" },
  payment_confirmed: { label: "Pago",              color: "success" },
  adding_funds:      { label: "Adicionando saldo", color: "primary" },
  ordering:          { label: "Criando pedido",    color: "primary" },
  in_progress:       { label: "Em andamento",      color: "secondary" },
  completed:         { label: "Concluído",          color: "success" },
  failed:            { label: "Falhou",             color: "danger" },
  cancelled:         { label: "Cancelado",          color: "default" },
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function TabButton({ active, onClick, icon, label, count }: {
  active: boolean; onClick: () => void; icon: any; label: string; count?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all border ${
        active
          ? "bg-primary/15 border-primary/30 text-primary"
          : "border-foreground/10 text-foreground/50 hover:text-foreground/80 hover:bg-foreground/5"
      }`}
    >
      <FontAwesomeIcon icon={icon} className="text-xs" />
      {label}
      {count !== undefined && (
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${active ? "bg-primary/20 text-primary" : "bg-foreground/10 text-foreground/40"}`}>
          {count}
        </span>
      )}
    </button>
  );
}

// ─── Config Tab ───────────────────────────────────────────────────────────────

function ConfigTab() {
  const [config, setConfig] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [checkingBalance, setCheckingBalance] = useState(false);
  const [cookie, setCookie] = useState("");
  const [cpf, setCpf] = useState("");
  const [balance, setBalance] = useState<any>(null);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    fetch("/api/admin/members/config", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => { if (d.success) setConfig(d.config); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      const body: any = {};
      if (cookie.trim()) body.revision_cookie = cookie.trim();
      if (cpf.trim()) body.revision_cpf = cpf.trim();
      if (!Object.keys(body).length) { setMsg({ type: "error", text: "Nenhum campo preenchido." }); return; }
      const r = await fetch("/api/admin/members/config", {
        method: "PUT", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (d.success) {
        setMsg({ type: "success", text: "Configurações salvas!" });
        setCookie(""); setCpf("");
        // Reload config
        const r2 = await fetch("/api/admin/members/config", { credentials: "include" });
        const d2 = await r2.json();
        if (d2.success) setConfig(d2.config);
      } else {
        setMsg({ type: "error", text: d.error || "Erro ao salvar." });
      }
    } finally { setSaving(false); }
  };

  const validate = async () => {
    setValidating(true); setValidationResult(null);
    try {
      const r = await fetch("/api/admin/members/config/validate", { method: "POST", credentials: "include" });
      const d = await r.json();
      setValidationResult(d);
    } finally { setValidating(false); }
  };

  const checkBalance = async () => {
    setCheckingBalance(true);
    try {
      const r = await fetch("/api/admin/members/config/balance", { credentials: "include" });
      const d = await r.json();
      setBalance(d);
    } finally { setCheckingBalance(false); }
  };

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="flex flex-col gap-5 max-w-2xl">

      {/* Current values */}
      <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-5 flex flex-col gap-4">
        <p className="text-sm font-bold text-foreground/60 uppercase tracking-wider">Estado atual</p>
        {[
          { key: "revision_cookie", label: "Cookie RevisionSMM" },
          { key: "revision_cpf", label: "CPF de pagamento" },
        ].map((item) => {
          const entry = config[item.key];
          return (
            <div key={item.key} className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold">{item.label}</p>
                <p className="text-xs font-mono text-foreground/40 mt-0.5">
                  {entry?.value || "Não configurado"}
                </p>
              </div>
              {entry?.updatedAt && (
                <span className="text-[10px] text-foreground/30">{fmtDate(entry.updatedAt)}</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Edit form */}
      <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-5 flex flex-col gap-4">
        <p className="text-sm font-bold text-foreground/60 uppercase tracking-wider">Atualizar configurações</p>

        <div className="flex flex-col gap-3">
          <div>
            <label className="text-xs font-semibold text-foreground/60 mb-1.5 block">Cookie RevisionSMM</label>
            <textarea
              value={cookie}
              onChange={(e) => setCookie(e.target.value)}
              rows={3}
              placeholder="Cole o cookie aqui…"
              className="w-full px-4 py-3 bg-foreground/5 border border-foreground/10 rounded-xl text-xs font-mono focus:outline-none focus:border-primary/40 transition-all resize-none placeholder:text-foreground/25"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-foreground/60 mb-1.5 block">CPF para PIX</label>
            <input
              value={cpf}
              onChange={(e) => setCpf(e.target.value)}
              placeholder="000.000.000-00"
              className="w-full px-4 py-3 bg-foreground/5 border border-foreground/10 rounded-xl text-sm font-mono focus:outline-none focus:border-primary/40 transition-all placeholder:text-foreground/25"
            />
          </div>
        </div>

        {msg && (
          <div className={`flex items-center gap-2 text-sm px-3 py-2 rounded-xl ${msg.type === "success" ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-red-500/10 border border-red-500/20 text-red-400"}`}>
            <FontAwesomeIcon icon={msg.type === "success" ? faCircleCheck : faTriangleExclamation} className="text-xs" />
            {msg.text}
          </div>
        )}

        <Button color="primary" isLoading={saving} onPress={save} startContent={!saving && <FontAwesomeIcon icon={faSave} className="text-xs" />}>
          Salvar configurações
        </Button>
      </div>

      {/* Actions */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-4 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <FontAwesomeIcon icon={faKey} className="text-primary text-sm" />
            <p className="text-sm font-bold">Validar Cookie</p>
          </div>
          <p className="text-xs text-foreground/45 leading-relaxed">Testa se o cookie atual ainda é válido na RevisionSMM.</p>

          {validationResult && (
            <div className={`text-xs px-3 py-2 rounded-lg ${validationResult.valid ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
              {validationResult.valid ? "✓ Cookie válido" : `✗ ${validationResult.error || "Inválido"}`}
            </div>
          )}

          <Button size="sm" variant="flat" isLoading={validating} onPress={validate}>
            Validar agora
          </Button>
        </div>

        <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-4 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <FontAwesomeIcon icon={faWallet} className="text-primary text-sm" />
            <p className="text-sm font-bold">Saldo</p>
          </div>
          <p className="text-xs text-foreground/45 leading-relaxed">Consulta o saldo atual da conta RevisionSMM.</p>

          {balance && (
            <div className={`text-xs px-3 py-2 rounded-lg ${balance.success ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
              {balance.success ? `Saldo: $${balance.balance ?? "—"}` : balance.error || "Erro"}
            </div>
          )}

          <Button size="sm" variant="flat" isLoading={checkingBalance} onPress={checkBalance}>
            Ver saldo
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Services Tab ─────────────────────────────────────────────────────────────

const EMPTY_SVC: RevisionService = {
  id: "", name: "", type: "online", description: "",
  pricePerUnit: 0, minQty: 100, maxQty: 10000,
};

function ServicesTab() {
  const [services, setServices] = useState<RevisionService[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<RevisionService | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/admin/members/services", { credentials: "include" });
      const d = await r.json();
      if (d.success) setServices(d.services ?? []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const saveAll = async (updated: RevisionService[]) => {
    setSaving(true); setMsg(null);
    try {
      const r = await fetch("/api/admin/members/services", {
        method: "PUT", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ services: updated }),
      });
      const d = await r.json();
      if (d.success) { setMsg({ type: "success", text: `${d.count} serviço(s) salvos.` }); setServices(updated); }
      else setMsg({ type: "error", text: d.error || "Erro ao salvar." });
    } finally { setSaving(false); }
  };

  const handleSaveEditing = () => {
    if (!editing) return;
    if (!editing.id || !editing.name || !editing.pricePerUnit) {
      setMsg({ type: "error", text: "Preencha id, nome e preço." }); return;
    }
    const next = isNew
      ? [...services, editing]
      : services.map((s) => s.id === editing.id ? editing : s);
    setEditing(null);
    saveAll(next);
  };

  const handleDelete = (id: string) => {
    if (!confirm("Remover este serviço?")) return;
    saveAll(services.filter((s) => s.id !== id));
  };

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-foreground/50">{services.length} serviço(s) cadastrado(s)</p>
        <Button
          size="sm" color="primary"
          startContent={<FontAwesomeIcon icon={faPlus} className="text-xs" />}
          onPress={() => { setEditing({ ...EMPTY_SVC }); setIsNew(true); }}
        >
          Novo serviço
        </Button>
      </div>

      {msg && (
        <div className={`flex items-center gap-2 text-sm px-3 py-2 rounded-xl ${msg.type === "success" ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-red-500/10 border border-red-500/20 text-red-400"}`}>
          <FontAwesomeIcon icon={msg.type === "success" ? faCircleCheck : faTriangleExclamation} className="text-xs" />
          {msg.text}
        </div>
      )}

      {/* Editing form */}
      <AnimatePresence>
        {editing && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="rounded-2xl border border-primary/25 bg-primary/[0.04] p-5 flex flex-col gap-4"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm font-bold">{isNew ? "Novo serviço" : "Editar serviço"}</p>
              <button onClick={() => setEditing(null)} className="text-foreground/40 hover:text-foreground/80">
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { label: "ID único", key: "id", placeholder: "ex: online-members", type: "text" },
                { label: "Nome", key: "name", placeholder: "ex: Members Online", type: "text" },
              ].map((f) => (
                <div key={f.key}>
                  <label className="text-xs font-semibold text-foreground/55 mb-1.5 block">{f.label}</label>
                  <input
                    value={(editing as any)[f.key]}
                    onChange={(e) => setEditing({ ...editing, [f.key]: e.target.value })}
                    placeholder={f.placeholder}
                    disabled={!isNew && f.key === "id"}
                    className="w-full px-3 py-2.5 text-sm bg-foreground/5 border border-foreground/10 rounded-xl focus:outline-none focus:border-primary/40 transition-all disabled:opacity-40 placeholder:text-foreground/25"
                  />
                </div>
              ))}

              <div>
                <label className="text-xs font-semibold text-foreground/55 mb-1.5 block">Tipo</label>
                <div className="flex gap-2">
                  {(["online", "offline"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setEditing({ ...editing, type: t })}
                      className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border text-sm font-semibold transition-all ${
                        editing.type === t
                          ? t === "online"
                            ? "bg-emerald-500/15 border-emerald-500/35 text-emerald-400"
                            : "bg-primary/15 border-primary/35 text-primary"
                          : "bg-foreground/5 border-foreground/10 text-foreground/50"
                      }`}
                    >
                      <FontAwesomeIcon icon={t === "online" ? faWifi : faUserSecret} className="text-xs" />
                      {t === "online" ? "Online" : "Offline"}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground/55 mb-1.5 block">Preço por unidade (R$)</label>
                <input
                  type="number" step="0.001" min="0"
                  value={editing.pricePerUnit}
                  onChange={(e) => setEditing({ ...editing, pricePerUnit: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-2.5 text-sm bg-foreground/5 border border-foreground/10 rounded-xl focus:outline-none focus:border-primary/40 transition-all"
                />
                <p className="text-[10px] text-foreground/35 mt-1">
                  1000 unidades = {fmtBRL(editing.pricePerUnit * 1000)}
                </p>
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground/55 mb-1.5 block">Qtd. mínima</label>
                <input
                  type="number" min="1"
                  value={editing.minQty}
                  onChange={(e) => setEditing({ ...editing, minQty: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2.5 text-sm bg-foreground/5 border border-foreground/10 rounded-xl focus:outline-none focus:border-primary/40 transition-all"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground/55 mb-1.5 block">Qtd. máxima</label>
                <input
                  type="number" min="1"
                  value={editing.maxQty}
                  onChange={(e) => setEditing({ ...editing, maxQty: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2.5 text-sm bg-foreground/5 border border-foreground/10 rounded-xl focus:outline-none focus:border-primary/40 transition-all"
                />
              </div>

              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-foreground/55 mb-1.5 block">Descrição (opcional)</label>
                <input
                  value={editing.description ?? ""}
                  onChange={(e) => setEditing({ ...editing, description: e.target.value })}
                  placeholder="Descrição exibida ao cliente"
                  className="w-full px-3 py-2.5 text-sm bg-foreground/5 border border-foreground/10 rounded-xl focus:outline-none focus:border-primary/40 transition-all placeholder:text-foreground/25"
                />
              </div>
            </div>

            <div className="flex gap-3">
              <Button variant="flat" onPress={() => setEditing(null)}>Cancelar</Button>
              <Button color="primary" isLoading={saving} onPress={handleSaveEditing}>
                Salvar
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* List */}
      {services.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-foreground/30">
          <FontAwesomeIcon icon={faUsers} className="text-4xl opacity-20" />
          <p className="text-sm">Nenhum serviço cadastrado.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {services.map((svc) => (
            <div key={svc.id} className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-4 flex items-center gap-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm shrink-0 ${svc.type === "online" ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-primary/10 border border-primary/20 text-primary"}`}>
                <FontAwesomeIcon icon={svc.type === "online" ? faWifi : faUserSecret} />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <p className="text-sm font-bold truncate">{svc.name}</p>
                  <span className="text-[10px] font-mono text-foreground/35">{svc.id}</span>
                  <Chip size="sm" color={svc.type === "online" ? "success" : "default"} variant="flat" className="text-[10px]">
                    {svc.type}
                  </Chip>
                </div>
                <div className="flex items-center gap-3 text-xs text-foreground/45">
                  <span>{fmtBRL(svc.pricePerUnit)}/un</span>
                  <span>·</span>
                  <span>{svc.minQty.toLocaleString("pt-BR")} – {svc.maxQty.toLocaleString("pt-BR")}</span>
                  <span>·</span>
                  <span className="text-primary font-semibold">1000un = {fmtBRL(svc.pricePerUnit * 1000)}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Button
                  size="sm" variant="flat" isIconOnly
                  onPress={() => { setEditing({ ...svc }); setIsNew(false); }}
                >
                  <FontAwesomeIcon icon={faPen} className="text-xs" />
                </Button>
                <Button
                  size="sm" variant="flat" color="danger" isIconOnly
                  onPress={() => handleDelete(svc.id)}
                >
                  <FontAwesomeIcon icon={faTrash} className="text-xs" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Orders Tab ───────────────────────────────────────────────────────────────

function OrdersTab() {
  const [orders, setOrders] = useState<MemberOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<MemberOrder | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [checking, setChecking] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ page: String(page), limit: "15" });
      if (statusFilter) qs.set("status", statusFilter);
      const r = await fetch(`/api/admin/members/orders?${qs}`, { credentials: "include" });
      const d = await r.json();
      if (d.success) {
        setOrders(d.orders ?? []);
        setPages(d.pages ?? 1);
        setTotal(d.total ?? 0);
      }
    } finally { setLoading(false); }
  }, [page, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const retry = async (id: string) => {
    setRetrying(id); setActionMsg(null);
    try {
      const r = await fetch(`/api/admin/members/orders/${id}/retry`, { method: "POST", credentials: "include" });
      const d = await r.json();
      setActionMsg(d.success ? "Reprocessado com sucesso!" : d.error || "Erro.");
      if (d.success) load();
    } finally { setRetrying(null); }
  };

  const checkRevision = async (id: string) => {
    setChecking(id); setActionMsg(null);
    try {
      const r = await fetch(`/api/admin/members/orders/${id}/check-revision`, { method: "POST", credentials: "include" });
      const d = await r.json();
      setActionMsg(d.success ? `Status Revision: ${d.revisionData?.status ?? "ok"}` : d.error || "Erro.");
      if (d.success) load();
    } finally { setChecking(null); }
  };

  const STATUSES = ["", "awaiting_payment", "payment_confirmed", "in_progress", "completed", "failed", "cancelled"];

  return (
    <div className="flex flex-col gap-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <FontAwesomeIcon icon={faFilter} className="text-foreground/30 text-xs" />
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => { setStatusFilter(s); setPage(1); }}
            className={`text-xs px-3 py-1.5 rounded-lg border font-semibold transition-all ${
              statusFilter === s
                ? "bg-primary/15 border-primary/30 text-primary"
                : "border-foreground/10 text-foreground/45 hover:border-foreground/25"
            }`}
          >
            {s ? (STATUS_CONFIG[s]?.label ?? s) : "Todos"}
          </button>
        ))}
        <span className="ml-auto text-xs text-foreground/35">{total} pedido(s)</span>
      </div>

      {actionMsg && (
        <div className="text-xs text-primary bg-primary/10 border border-primary/20 rounded-lg px-3 py-2">
          {actionMsg}
        </div>
      )}

      {/* Table */}
      <div className="rounded-2xl border border-foreground/10 overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : orders.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-12 text-foreground/30">
            <FontAwesomeIcon icon={faListCheck} className="text-3xl opacity-20" />
            <p className="text-sm">Nenhum pedido encontrado.</p>
          </div>
        ) : (
          <div className="divide-y divide-foreground/5">
            {/* Header */}
            <div className="hidden md:grid grid-cols-[1fr_auto_auto_auto_auto] gap-4 px-4 py-2.5 text-[10px] font-bold text-foreground/35 uppercase tracking-wider">
              <span>Pedido</span>
              <span>Qtd.</span>
              <span>Total</span>
              <span>Status</span>
              <span>Ações</span>
            </div>

            {orders.map((o) => {
              const stCfg = STATUS_CONFIG[o.status] ?? { label: o.status, color: "default" as const };
              return (
                <div key={o._id} className="grid grid-cols-1 md:grid-cols-[1fr_auto_auto_auto_auto] gap-3 md:gap-4 px-4 py-3 hover:bg-foreground/[0.02] transition-colors items-center">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-mono text-foreground/35">{o._id.slice(-8)}</span>
                      <span className="text-sm font-semibold truncate">{o.serviceName}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-foreground/40 mt-0.5">
                      <span>{o.userId?.username ?? o.userId?.email ?? "—"}</span>
                      <span>·</span>
                      <span>{fmtDate(o.createdAt)}</span>
                      {o.revision.orderId && (
                        <><span>·</span><span className="font-mono">Rev#{o.revision.orderId}</span></>
                      )}
                    </div>
                  </div>

                  <span className="text-sm font-semibold">{o.quantity.toLocaleString("pt-BR")}</span>

                  <span className="text-sm font-bold text-primary">{fmtBRL(o.totalCharged)}</span>

                  <Chip size="sm" color={stCfg.color} variant="flat" className="text-[10px]">
                    {stCfg.label}
                  </Chip>

                  <div className="flex items-center gap-1.5">
                    <Button
                      size="sm" variant="flat" isIconOnly
                      title="Ver detalhes"
                      onPress={() => setSelected(o)}
                    >
                      <FontAwesomeIcon icon={faEye} className="text-xs" />
                    </Button>
                    {["failed", "payment_confirmed", "adding_funds", "ordering"].includes(o.status) && (
                      <Button
                        size="sm" variant="flat" color="warning" isIconOnly
                        title="Retentar"
                        isLoading={retrying === o._id}
                        onPress={() => retry(o._id)}
                      >
                        {retrying !== o._id && <FontAwesomeIcon icon={faRotate} className="text-xs" />}
                      </Button>
                    )}
                    {o.revision.orderId && (
                      <Button
                        size="sm" variant="flat" isIconOnly
                        title="Checar Revision"
                        isLoading={checking === o._id}
                        onPress={() => checkRevision(o._id)}
                      >
                        {checking !== o._id && <FontAwesomeIcon icon={faBolt} className="text-xs" />}
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Pagination */}
      {!loading && total > 0 && (
        <div className="flex items-center justify-between text-xs text-foreground/40">
          <span>{total} pedido(s)</span>
          <div className="flex items-center gap-2">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="p-1.5 hover:bg-foreground/10 rounded-lg disabled:opacity-30 transition-colors">
              <FontAwesomeIcon icon={faChevronLeft} className="text-xs" />
            </button>
            <span>Pág. <strong>{page}</strong> / <strong>{pages}</strong></span>
            <button disabled={page >= pages} onClick={() => setPage((p) => p + 1)} className="p-1.5 hover:bg-foreground/10 rounded-lg disabled:opacity-30 transition-colors">
              <FontAwesomeIcon icon={faChevronRight} className="text-xs" />
            </button>
          </div>
        </div>
      )}

      {/* Detail drawer */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-end md:items-center justify-center p-4"
            onClick={() => setSelected(null)}
          >
            <motion.div
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 40, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-lg bg-background border border-foreground/10 rounded-2xl p-6 flex flex-col gap-4 max-h-[90vh] overflow-y-auto"
            >
              <div className="flex items-center justify-between">
                <p className="font-bold">Pedido #{selected._id.slice(-8)}</p>
                <button onClick={() => setSelected(null)} className="text-foreground/40 hover:text-foreground/80">
                  <FontAwesomeIcon icon={faXmark} />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm">
                {[
                  ["Serviço", selected.serviceName],
                  ["Quantidade", selected.quantity.toLocaleString("pt-BR")],
                  ["Servidor", selected.serverLink],
                  ["Guild ID", selected.guildId || "—"],
                  ["Total", fmtBRL(selected.totalCharged)],
                  ["Status pagamento", selected.payment.status],
                  ["Mistic ID", selected.payment.misticId || "—"],
                  ["Pago em", selected.payment.paidAt ? fmtDate(selected.payment.paidAt) : "—"],
                  ["Revision ID", selected.revision.orderId || "—"],
                  ["Status Revision", selected.revision.orderStatus || "—"],
                  ["Add Funds", selected.revision.addFundsStatus || "—"],
                  ["Criado em", fmtDate(selected.createdAt)],
                ].map(([k, v]) => (
                  <div key={k}>
                    <p className="text-[10px] text-foreground/40 mb-0.5">{k}</p>
                    <p className="text-xs font-semibold break-all">{v}</p>
                  </div>
                ))}
              </div>

              {selected.failReason && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/15 rounded-xl p-3">
                  <p className="font-bold mb-1">Motivo da falha</p>
                  <p className="font-mono">{selected.failReason}</p>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Stats Tab ────────────────────────────────────────────────────────────────

function StatsTab() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/admin/members/stats", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => { if (d.success) setStats(d.stats); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (!stats) return <p className="text-sm text-foreground/40">Erro ao carregar estatísticas.</p>;

  return (
    <div className="flex flex-col gap-5">
      {/* Revenue */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Receita total", value: fmtBRL(stats.totalRevenue ?? 0), accent: "emerald" },
          { label: "Nossas taxas", value: fmtBRL(stats.totalOurFees ?? 0), accent: "primary" },
          { label: "Pedidos (24h)", value: String(stats.ordersLast24h ?? 0), accent: "blue" },
        ].map((c) => (
          <div key={c.label} className={`rounded-2xl border p-5 ${c.accent === "emerald" ? "border-emerald-500/20 bg-emerald-500/[0.04]" : c.accent === "primary" ? "border-primary/20 bg-primary/[0.04]" : "border-blue-500/20 bg-blue-500/[0.04]"}`}>
            <p className="text-xs text-foreground/50 mb-1">{c.label}</p>
            <p className="text-2xl font-black">{c.value}</p>
          </div>
        ))}
      </div>

      {/* By status */}
      <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-5">
        <p className="text-sm font-bold mb-4">Pedidos por status</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(stats.byStatus ?? {}).map(([status, count]) => {
            const cfg = STATUS_CONFIG[status] ?? { label: status, color: "default" as const };
            return (
              <div key={status} className="flex items-center justify-between p-3 rounded-xl bg-foreground/[0.03] border border-foreground/8">
                <div className="flex items-center gap-2">
                  <Chip size="sm" color={cfg.color} variant="flat" className="text-[10px]">{cfg.label}</Chip>
                </div>
                <span className="font-black text-lg">{count as number}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AdminMembersPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useRequireAdmin();
  const [tab, setTab] = useState<Tab>("config");

  if (authLoading) return <Loading />;
  if (!user?.admin) return <Loading />;

  const TABS: { id: Tab; label: string; icon: any }[] = [
    { id: "config",   label: "Configuração", icon: faGear },
    { id: "services", label: "Serviços",     icon: faUsers },
    { id: "orders",   label: "Pedidos",      icon: faListCheck },
    { id: "stats",    label: "Estatísticas", icon: faChartBar },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-4 py-8 flex flex-col gap-6">

        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/dashboard/admin?tab=services")}
            className="w-9 h-9 rounded-xl border border-foreground/10 flex items-center justify-center text-foreground/50 hover:text-foreground/80 hover:bg-foreground/5 transition-all"
          >
            <FontAwesomeIcon icon={faArrowLeft} className="text-sm" />
          </button>

          <div className="w-11 h-11 rounded-xl bg-primary/15 border border-primary/25 flex items-center justify-center text-primary text-lg">
            <FontAwesomeIcon icon={faUsers} />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <p className="text-xs text-foreground/35">Serviços</p>
              <span className="text-foreground/20">/</span>
              <p className="text-xs text-foreground/60 font-semibold">Members</p>
            </div>
            <h1 className="text-2xl font-black leading-tight">Gerenciar Members</h1>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex flex-wrap gap-2">
          {TABS.map((t) => (
            <TabButton
              key={t.id}
              active={tab === t.id}
              onClick={() => setTab(t.id)}
              icon={t.icon}
              label={t.label}
            />
          ))}
        </div>

        {/* Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            {tab === "config"   && <ConfigTab />}
            {tab === "services" && <ServicesTab />}
            {tab === "orders"   && <OrdersTab />}
            {tab === "stats"    && <StatsTab />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}