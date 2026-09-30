"use client";

import { useEffect, useState, useRef } from "react";
import { Button, Input, Select, SelectItem, Pagination, Spinner, Textarea, Chip } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faSearch,
  faRefresh,
  faRotate,
  faSpinner,
  faCheckCircle,
  faTimesCircle,
  faSave,
  faInfoCircle,
  faChevronDown,
  faChevronUp,
} from "@fortawesome/free-solid-svg-icons";
import { SectionHeader } from "@/components/layout/SectionHeader";
import { ApplicationCard } from "./ApplicationCard";
import { ApplicationModal } from "./ApplicationModal";
import { AuditTable } from "./AuditTable";
import { ApplicationStats } from "./ApplicationStats";
import { RequirementsSection } from "../bot/RequirementsSection";
import { Application } from "@/types/application";

// ─── Bot Bio Panel ────────────────────────────────────────────────────────────

function BotBioPanel({ onClose }: { onClose: () => void }) {
  const [bio, setBio] = useState("");
  const [originalBio, setOriginalBio] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadBio = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/admin/bot/bio");
      if (res.ok) {
        const data = await res.json();
        setBio(data.bio || "");
        setOriginalBio(data.bio || "");
        setUpdatedAt(data.updatedAt);
      }
    } catch {
      // silencioso
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBio();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage(null);
      const res = await fetch("/api/admin/bot/bio", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bio }),
      });
      const data = await res.json();
      if (res.ok) {
        setOriginalBio(bio);
        setUpdatedAt(data.updatedAt);
        setMessage({ type: "success", text: "Bio salva! Os bots vão buscar a atualização no próximo ciclo (1 min)." });
        setTimeout(() => setMessage(null), 4000);
      } else {
        setMessage({ type: "error", text: data.error || "Erro ao salvar" });
      }
    } catch {
      setMessage({ type: "error", text: "Erro de conexão" });
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = bio !== originalBio;

  return (
    <div className="rounded-xl border border-foreground/15 bg-foreground/[0.03] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-foreground/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-foreground/8">
            <FontAwesomeIcon icon={faInfoCircle} className="text-sm text-foreground/60" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">Biografia Global dos Bots</h3>
            <p className="text-xs text-foreground/50">
              Todos os bots buscam essa bio da API a cada 1 minuto
              {updatedAt && (
                <span className="ml-2 opacity-60">
                  · atualizado {new Date(updatedAt).toLocaleString("pt-BR")}
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="light"
            isDisabled={loading || saving}
            onPress={loadBio}
            isIconOnly
            className="text-foreground/40 hover:text-foreground/80"
          >
            <FontAwesomeIcon icon={faRotate} className={loading ? "animate-spin" : ""} />
          </Button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving || loading}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
              hasChanges && !saving && !loading
                ? "bg-primary text-white hover:bg-primary/90"
                : "bg-foreground/8 text-foreground/30 cursor-not-allowed"
            }`}
          >
            {saving ? (
              <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
            ) : (
              <FontAwesomeIcon icon={faSave} />
            )}
            Salvar Bio
          </button>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-foreground/40 hover:text-foreground/80 hover:bg-foreground/8 transition-all text-xs"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="px-5 py-4 space-y-3">
        {loading ? (
          <div className="h-16 rounded-lg bg-foreground/5 animate-pulse" />
        ) : (
          <textarea
            value={bio}
            onChange={(e) => {
              setBio(e.target.value);
              setMessage(null);
            }}
            placeholder="Digite a bio que todos os bots vão exibir no Discord..."
            maxLength={400}
            rows={3}
            className="w-full bg-foreground/5 border border-foreground/10 rounded-lg px-3 py-2.5 text-sm font-mono resize-none outline-none focus:border-primary/40 focus:bg-foreground/8 transition-all placeholder:text-foreground/25 text-foreground"
          />
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-foreground/40">
            <FontAwesomeIcon icon={faInfoCircle} className="text-[10px]" />
            <span>
              Se vazio, os bots usam o fallback local.{" "}
              <code className="bg-foreground/8 px-1 rounded">GET /bot/bio</code> com{" "}
              <code className="bg-foreground/8 px-1 rounded">botToken</code>
            </span>
          </div>
          <span className="text-xs font-mono text-foreground/30">{bio.length}/400</span>
        </div>

        {/* Feedback */}
        {message && (
          <div
            className={`text-xs px-3 py-2 rounded-lg border flex items-center gap-2 ${
              message.type === "success"
                ? "bg-success/8 border-success/20 text-success-600"
                : "bg-danger/8 border-danger/20 text-danger-600"
            }`}
          >
            <FontAwesomeIcon
              icon={message.type === "success" ? faCheckCircle : faTimesCircle}
              className="text-[10px]"
            />
            {message.text}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Mass Restart Banner ──────────────────────────────────────────────────────

interface RestartJob {
  appId: string;
  name: string;
  status: "pending" | "restarting" | "done" | "error";
}

function MassRestartBanner({ onClose }: { onClose: () => void }) {
  const [phase, setPhase] = useState<"idle" | "fetching" | "running" | "done">("idle");
  const [jobs, setJobs] = useState<RestartJob[]>([]);
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [successCount, setSuccessCount] = useState(0);
  const [errorCount, setErrorCount] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef(false);

  const fetchApps = async (): Promise<{ _id: string; name: string; hosting?: { appId?: string } }[]> => {
    const all: any[] = [];
    let page = 1;
    while (true) {
      const res = await fetch(`/api/admin/applications?page=${page}&limit=100&sortBy=createdAt&sortOrder=desc`);
      if (!res.ok) break;
      const data = await res.json();
      const apps = data.applications || [];
      all.push(...apps);
      if (all.length >= (data.pagination?.total || 0) || apps.length < 100) break;
      page++;
    }
    return all;
  };

  const startRestart = async () => {
    cancelRef.current = false;
    setPhase("fetching");
    setSuccessCount(0);
    setErrorCount(0);

    const apps = await fetchApps();
    const eligible = apps.filter((a) => a.hosting?.appId);

    const initialJobs: RestartJob[] = eligible.map((a) => ({
      appId: a._id,
      name: a.name,
      status: "pending",
    }));

    setJobs(initialJobs);
    setPhase("running");

    let sc = 0;
    let ec = 0;

    for (let i = 0; i < initialJobs.length; i++) {
      if (cancelRef.current) break;

      setCurrentIdx(i);
      setJobs((prev) =>
        prev.map((j, idx) => (idx === i ? { ...j, status: "restarting" } : j))
      );

      setTimeout(() => {
        (scrollRef.current?.children[i] as HTMLElement)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }, 50);

      try {
        const res = await fetch(`/api/admin/applications/${initialJobs[i].appId}/restart`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        if (res.ok) {
          sc++;
          setSuccessCount(sc);
          setJobs((prev) =>
            prev.map((j, idx) => (idx === i ? { ...j, status: "done" } : j))
          );
        } else {
          throw new Error();
        }
      } catch {
        ec++;
        setErrorCount(ec);
        setJobs((prev) =>
          prev.map((j, idx) => (idx === i ? { ...j, status: "error" } : j))
        );
      }

      await new Promise((r) => setTimeout(r, 400));
    }

    setPhase("done");
    setCurrentIdx(-1);
  };

  const reset = () => {
    cancelRef.current = true;
    setPhase("idle");
    setJobs([]);
    setCurrentIdx(-1);
    setSuccessCount(0);
    setErrorCount(0);
  };

  const progress =
    jobs.length > 0 ? Math.round(((successCount + errorCount) / jobs.length) * 100) : 0;

  return (
    <div className="rounded-xl border border-foreground/15 bg-foreground/[0.03] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-foreground/10">
        <div className="flex items-center gap-3">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              phase === "running" || phase === "fetching"
                ? "bg-primary/15"
                : phase === "done"
                ? "bg-success/15"
                : "bg-foreground/8"
            }`}
          >
            <FontAwesomeIcon
              icon={
                phase === "running" || phase === "fetching"
                  ? faSpinner
                  : phase === "done"
                  ? faCheckCircle
                  : faRotate
              }
              className={`text-sm ${
                phase === "running" || phase === "fetching"
                  ? "text-primary animate-spin"
                  : phase === "done"
                  ? "text-success"
                  : "text-foreground/60"
              }`}
            />
          </div>
          <div>
            <h3 className="text-sm font-semibold">Reinicialização em Massa</h3>
            <p className="text-xs text-foreground/50">
              {phase === "idle" && "Reinicia todas as aplicações com hospedagem ativa"}
              {phase === "fetching" && "Buscando aplicações..."}
              {phase === "running" && `Reiniciando ${currentIdx + 1} de ${jobs.length}...`}
              {phase === "done" && `Concluído — ${successCount} ok, ${errorCount} erro(s)`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {phase === "idle" && (
            <button
              onClick={startRestart}
              className="px-4 py-1.5 rounded-lg bg-primary text-white text-xs font-semibold hover:bg-primary/90 transition-all flex items-center gap-2"
            >
              <FontAwesomeIcon icon={faRotate} />
              Reiniciar Todas
            </button>
          )}
          {(phase === "running" || phase === "fetching") && (
            <button
              onClick={() => { cancelRef.current = true; }}
              className="px-4 py-1.5 rounded-lg bg-danger/15 text-danger text-xs font-semibold hover:bg-danger/25 transition-all"
            >
              Cancelar
            </button>
          )}
          {phase === "done" && (
            <button
              onClick={reset}
              className="px-4 py-1.5 rounded-lg bg-foreground/8 text-foreground/70 text-xs font-semibold hover:bg-foreground/15 transition-all"
            >
              Limpar
            </button>
          )}
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-foreground/40 hover:text-foreground/80 hover:bg-foreground/8 transition-all text-xs"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Barra de progresso */}
      {(phase === "running" || phase === "fetching" || phase === "done") && (
        <div className="px-5 py-3 border-b border-foreground/10">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-3 text-xs text-foreground/60">
              <span className="flex items-center gap-1 text-success">
                <FontAwesomeIcon icon={faCheckCircle} className="text-[10px]" />
                {successCount} ok
              </span>
              <span className="flex items-center gap-1 text-danger">
                <FontAwesomeIcon icon={faTimesCircle} className="text-[10px]" />
                {errorCount} erro(s)
              </span>
              {jobs.length > 0 && (
                <span className="text-foreground/40">{jobs.length} total</span>
              )}
            </div>
            <span className="text-xs font-mono text-foreground/50">{progress}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-foreground/8 overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Lista de jobs */}
      {jobs.length > 0 && (
        <div ref={scrollRef} className="max-h-52 overflow-y-auto divide-y divide-foreground/5">
          {jobs.map((job, idx) => (
            <div
              key={job.appId}
              className={`flex items-center justify-between px-5 py-2.5 transition-colors ${
                idx === currentIdx
                  ? "bg-primary/8"
                  : job.status === "done"
                  ? "bg-success/[0.03]"
                  : job.status === "error"
                  ? "bg-danger/[0.03]"
                  : ""
              }`}
            >
              <div className="flex items-center gap-2.5">
                <div className="w-5 flex justify-center">
                  {job.status === "pending" && (
                    <span className="w-1.5 h-1.5 rounded-full bg-foreground/20 block" />
                  )}
                  {job.status === "restarting" && (
                    <FontAwesomeIcon icon={faSpinner} className="text-primary text-xs animate-spin" />
                  )}
                  {job.status === "done" && (
                    <FontAwesomeIcon icon={faCheckCircle} className="text-success text-xs" />
                  )}
                  {job.status === "error" && (
                    <FontAwesomeIcon icon={faTimesCircle} className="text-danger text-xs" />
                  )}
                </div>
                <span className={`text-xs font-medium ${idx === currentIdx ? "text-primary" : "text-foreground/70"}`}>
                  {job.name}
                </span>
              </div>
              <span
                className={`text-[10px] font-mono ${
                  job.status === "pending"
                    ? "text-foreground/30"
                    : job.status === "restarting"
                    ? "text-primary"
                    : job.status === "done"
                    ? "text-success"
                    : "text-danger"
                }`}
              >
                {job.status === "pending"
                  ? "aguardando"
                  : job.status === "restarting"
                  ? "reiniciando..."
                  : job.status === "done"
                  ? "ok"
                  : "erro"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Top Controls (Bio + Restart + Requirements) ──────────────────────────────

function TopControls() {
  const [showRestart, setShowRestart] = useState(true);
  const [showBio, setShowBio] = useState(true);
  const [showReqs, setShowReqs] = useState(true);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="space-y-2">
      {/* Linha de toggle */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-foreground/40 hover:text-foreground/70 transition-colors"
        >
          <FontAwesomeIcon icon={collapsed ? faChevronDown : faChevronUp} className="text-[10px]" />
          {collapsed ? "Mostrar ferramentas" : "Ocultar ferramentas"}
        </button>

        {!collapsed && (
          <div className="flex items-center gap-2 ml-auto">
            {!showBio && (
              <button
                onClick={() => setShowBio(true)}
                className="flex items-center gap-1.5 text-xs text-foreground/50 hover:text-foreground/80 transition-colors"
              >
                <FontAwesomeIcon icon={faInfoCircle} className="text-[10px]" />
                Bio Global
              </button>
            )}
            {!showRestart && (
              <button
                onClick={() => setShowRestart(true)}
                className="flex items-center gap-1.5 text-xs text-foreground/50 hover:text-foreground/80 transition-colors"
              >
                <FontAwesomeIcon icon={faRotate} className="text-[10px]" />
                Reinicialização em massa
              </button>
            )}
            {!showReqs && (
              <button
                onClick={() => setShowReqs(true)}
                className="flex items-center gap-1.5 text-xs text-foreground/50 hover:text-foreground/80 transition-colors"
              >
                <FontAwesomeIcon icon={faSearch} className="text-[10px]" />
                Requirements
              </button>
            )}
          </div>
        )}
      </div>

      {/* Painéis */}
      {!collapsed && (showBio || showRestart || showReqs) && (
        <div className="space-y-3">
          {/* Bio + Restart lado a lado */}
          {(showBio || showRestart) && (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
              {showBio && <BotBioPanel onClose={() => setShowBio(false)} />}
              {showRestart && <MassRestartBanner onClose={() => setShowRestart(false)} />}
            </div>
          )}

          {/* Requirements em largura total */}
          {showReqs && (
            <div className="rounded-xl border border-foreground/15 bg-foreground/[0.03] overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-foreground/10">
                <p className="text-xs text-foreground/40 font-medium">requirements.txt Global</p>
                <button
                  onClick={() => setShowReqs(false)}
                  className="w-7 h-7 rounded-lg flex items-center justify-center text-foreground/40 hover:text-foreground/80 hover:bg-foreground/8 transition-all text-xs"
                >
                  ✕
                </button>
              </div>
              <div className="p-5">
                <RequirementsSection />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Section ─────────────────────────────────────────────────────────────

export function AplicacoesSection() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [plans, setPlans] = useState<any[]>([]);

  // Filtros
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [planFilter, setPlanFilter] = useState("");
  const [expiredFilter, setExpiredFilter] = useState("");
  const [blockedFilter, setBlockedFilter] = useState("");

  // Paginação
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 20;

  // Modal
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Auditoria
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [showAudit, setShowAudit] = useState(false);

  const loadApplications = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        page: String(page),
        limit: String(limit),
        search,
        status: statusFilter,
        planId: planFilter,
        expired: expiredFilter,
        blocked: blockedFilter,
        sortBy: "createdAt",
        sortOrder: "desc",
      });

      const res = await fetch(`/api/admin/applications?${params}`, { cache: "no-store" });

      if (!res.ok) throw new Error("Erro ao carregar aplicações");

      const data = await res.json();
      setApplications(data.applications || []);
      setTotal(data.pagination?.total || 0);
      setTotalPages(data.pagination?.totalPages || 1);
    } catch (err: any) {
      setError(err?.message || "Erro ao carregar aplicações");
      setApplications([]);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetch("/api/admin/applications/stats");
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats);
      }
    } catch {}
  };

  const loadAuditLogs = async () => {
    try {
      setAuditLoading(true);
      const res = await fetch(`/api/admin/applications/audit/logs?page=1&limit=50`);
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data.logs || []);
      }
    } catch {}
    finally { setAuditLoading(false); }
  };

  const loadPlans = async () => {
    try {
      const res = await fetch("/api/admin/plans/list");
      if (res.ok) {
        const data = await res.json();
        setPlans(data.plans || []);
      }
    } catch {}
  };

  useEffect(() => {
    loadApplications();
  }, [page, search, statusFilter, planFilter, expiredFilter, blockedFilter]);

  useEffect(() => {
    loadStats();
    loadAuditLogs();
    loadPlans();
  }, []);

  const handleAction = async (action: string, appId: string, data?: any) => {
    try {
      let url = `/api/admin/applications/${appId}`;
      let method = "POST";
      let body = data ? JSON.stringify(data) : JSON.stringify({});

      switch (action) {
        case "block":      url += "/block";   break;
        case "unblock":    url += "/unblock"; break;
        case "restart":    url += "/restart"; break;
        case "stop":       url += "/stop";    break;
        case "start":      url += "/start";   break;
        case "restore":    url += "/restore"; break;
        case "update":     method = "PUT";    break;
        case "changeRam":  url += "/ram"; method = "PUT"; break;
        case "delete":
          method = "DELETE";
          if (data?.deleteFrom) {
            url += `?deleteFrom=${data.deleteFrom}`;
            if (data.permanent !== undefined) url += `&permanent=${data.permanent}`;
          }
          break;
      }

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body,
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Erro na operação");
      }

      await loadApplications();
      await loadAuditLogs();

      if (modalOpen) {
        setModalOpen(false);
        setSelectedApp(null);
      }

      return true;
    } catch (err: any) {
      alert(err.message || "Erro na operação");
      return false;
    }
  };

  const openDetails = async (app: Application) => {
    try {
      const res = await fetch(`/api/admin/applications/${app._id}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedApp(data.application);
        setModalOpen(true);
      }
    } catch {}
  };

  if (loading && applications.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">

      {/* ── Topo: Bio Global + Reiniciar em Massa + Requirements ── */}
      <TopControls />

      {/* Header com ações */}
      <SectionHeader
        description="Gerencie todas as aplicações do sistema"
        actions={
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="light"
              onPress={() => setShowAudit(!showAudit)}
            >
              {showAudit ? "Ocultar" : "Mostrar"} Auditoria
            </Button>
            <Button
              size="sm"
              color="primary"
              onPress={loadApplications}
              startContent={<FontAwesomeIcon icon={faRefresh} />}
            >
              Atualizar
            </Button>
          </div>
        }
      />

      {/* Estatísticas */}
      {stats && <ApplicationStats stats={stats} />}

      {/* Filtros */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
        <Input
          size="sm"
          placeholder="Buscar por nome, Discord ID, plano..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          startContent={<FontAwesomeIcon icon={faSearch} className="text-foreground/50" />}
        />

        <Select
          size="sm"
          placeholder="Status"
          selectedKeys={statusFilter ? new Set([statusFilter]) : new Set()}
          onSelectionChange={(keys) => setStatusFilter(Array.from(keys)[0] as string || "")}
        >
          <SelectItem key="">Todos</SelectItem>
          <SelectItem key="online">Online</SelectItem>
          <SelectItem key="offline">Offline</SelectItem>
          <SelectItem key="maintenance">Manutenção</SelectItem>
        </Select>

        <Select
          size="sm"
          placeholder="Plano"
          selectedKeys={planFilter ? new Set([planFilter]) : new Set()}
          onSelectionChange={(keys) => setPlanFilter(Array.from(keys)[0] as string || "")}
        >
          <SelectItem key="">Todos</SelectItem>
          {plans.map((plan: any) => (
            <SelectItem key={plan.id} value={plan.id}>
              {plan.name}
            </SelectItem>
          ))}
        </Select>

        <Select
          size="sm"
          placeholder="Expiração"
          selectedKeys={expiredFilter ? new Set([expiredFilter]) : new Set()}
          onSelectionChange={(keys) => setExpiredFilter(Array.from(keys)[0] as string || "")}
        >
          <SelectItem key="">Todos</SelectItem>
          <SelectItem key="false">Ativos</SelectItem>
          <SelectItem key="true">Expirados</SelectItem>
        </Select>

        <Select
          size="sm"
          placeholder="Bloqueio"
          selectedKeys={blockedFilter ? new Set([blockedFilter]) : new Set()}
          onSelectionChange={(keys) => setBlockedFilter(Array.from(keys)[0] as string || "")}
        >
          <SelectItem key="">Todos</SelectItem>
          <SelectItem key="false">Desbloqueados</SelectItem>
          <SelectItem key="true">Bloqueados</SelectItem>
        </Select>
      </div>

      {/* Erro */}
      {error && (
        <div className="rounded-lg bg-danger/10 border border-danger/20 text-danger-500 text-sm p-3">
          {error}
        </div>
      )}

      {/* Grid de aplicações */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
        {applications.map((app) => (
          <ApplicationCard
            key={app._id}
            application={app}
            onView={() => openDetails(app)}
            onAction={(action, data) => handleAction(action, app._id, data)}
            onRefresh={loadApplications}
          />
        ))}
      </div>

      {/* Vazio */}
      {!loading && applications.length === 0 && (
        <div className="rounded-lg bg-foreground/5 border border-foreground/10 p-8 text-center">
          <p className="text-foreground/70">Nenhuma aplicação encontrada</p>
        </div>
      )}

      {/* Paginação */}
      {totalPages > 1 && (
        <div className="flex justify-center mt-4">
          <Pagination
            total={totalPages}
            page={page}
            onChange={setPage}
            size="sm"
            showControls
            boundaries={1}
            siblings={1}
          />
        </div>
      )}

      {/* Auditoria */}
      {showAudit && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-3">Logs de Auditoria</h3>
          <div className="rounded-lg border border-foreground/10 bg-foreground/2 p-4">
            <AuditTable logs={auditLogs} loading={auditLoading} />
          </div>
        </div>
      )}

      {/* Modal de detalhes */}
      {selectedApp && (
        <ApplicationModal
          application={selectedApp}
          isOpen={modalOpen}
          onClose={() => {
            setModalOpen(false);
            setSelectedApp(null);
          }}
          onAction={(action, data) => handleAction(action, selectedApp._id, data)}
        />
      )}
    </div>
  );
}
