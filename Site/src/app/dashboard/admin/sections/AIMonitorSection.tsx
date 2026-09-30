"use client";

/**
 * AIMonitorSection — Painel de monitoramento inteligente com CyM AI
 * 
 * Seção do painel admin que exibe:
 * - Status geral do monitor
 * - Cards de stats (apps, reinicios, erros, aguardando token)
 * - Feed de eventos em tempo real
 * - Resumo da CyM
 * - Chat interativo com a CyM sobre as apps
 * - Visualização de logs
 */

import { useEffect, useState, useRef, useCallback } from "react";
import { Button, Spinner, Chip } from "@heroui/react";
import {
  faBrain,
  faRotate,
  faServer,
  faExclamationTriangle,
  faKey,
  faCheckCircle,
  faTimesCircle,
  faCircleNotch,
  faClock,
  faFileAlt,
  faPaperPlane,
  faFilter,
  faArrowsRotate,
  faBolt,
  faMemory,
  faInfoCircle,
  faChevronDown,
  faChevronUp,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtRelative(dateStr) {
  if (!dateStr) return "—";
  const ms = Date.now() - new Date(dateStr).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60)  return `${s}s atrás`;
  const m = Math.floor(s / 60);
  if (m < 60)  return `${m}m atrás`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `${h}h atrás`;
  return `${Math.floor(h / 24)}d atrás`;
}

function fmtDate(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

const ACTION_META = {
  RESTARTED:       { label: "Reiniciado",          color: "success", icon: faRotate },
  RESTARTED_RAM:   { label: "Reiniciado (RAM)",     color: "warning", icon: faMemory },
  RESTART_FAILED:  { label: "Falha ao reiniciar",   color: "danger",  icon: faTimesCircle },
  WAIT_TOKEN:      { label: "Aguardando token",     color: "danger",  icon: faKey },
  WAITING_TOKEN:   { label: "Ainda sem token",      color: "danger",  icon: faKey },
  TOKEN_CLEARED:   { label: "Token confirmado",     color: "success", icon: faCheckCircle },
  REPORT_ONLY:     { label: "Erro reportado",       color: "warning", icon: faExclamationTriangle },
  RESTART_RAM:     { label: "RAM crítica",          color: "warning", icon: faMemory },
  RESTARTING:      { label: "Reiniciando...",       color: "primary", icon: faCircleNotch },
  WAIT:            { label: "Aguardando",           color: "default", icon: faClock },
  SKIP:            { label: "Sem status",           color: "default", icon: faInfoCircle },
  CYCLE_ERROR:     { label: "Erro de ciclo",        color: "danger",  icon: faTimesCircle },
  ERROR:           { label: "Erro",                 color: "danger",  icon: faTimesCircle },
  SUMMARY:         { label: "Resumo CyM",           color: "primary", icon: faBrain },
};

function getActionMeta(action) {
  return ACTION_META[action] || { label: action, color: "default", icon: faInfoCircle };
}

const LEVEL_COLOR = {
  INFO:    "text-foreground/80",
  WARN:    "text-warning-500",
  ERROR:   "text-danger-500",
  SUMMARY: "text-primary-400",
};

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, accent, sub }) {
  return (
    <div className={`relative overflow-hidden rounded-xl border ${accent} bg-foreground/[0.02] p-4`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-foreground/50 mb-1">{label}</p>
          <p className="text-2xl font-bold tabular-nums">{value ?? "—"}</p>
          {sub && <p className="text-xs text-foreground/40 mt-1">{sub}</p>}
        </div>
        <div className={`p-2 rounded-lg bg-foreground/5`}>
          <FontAwesomeIcon icon={icon} className="w-4 h-4 text-foreground/40" />
        </div>
      </div>
    </div>
  );
}

// ─── Event Row ────────────────────────────────────────────────────────────────

function EventRow({ event, onClearToken }) {
  const [expanded, setExpanded] = useState(false);
  const meta = getActionMeta(event.action);
  const hasDetails = event.aiAnalysis || event.details;

  return (
    <div className={`border-b border-foreground/5 last:border-0 px-4 py-3 hover:bg-foreground/[0.02] transition-colors ${
      event.level === "ERROR" ? "bg-danger/[0.02]" :
      event.level === "WARN"  ? "bg-warning/[0.02]" : ""
    }`}>
      <div className="flex items-start gap-3">
        {/* Ícone */}
        <div className="mt-0.5 shrink-0">
          <FontAwesomeIcon
            icon={meta.icon}
            className={`w-3.5 h-3.5 ${
              meta.color === "success" ? "text-success-500" :
              meta.color === "danger"  ? "text-danger-500"  :
              meta.color === "warning" ? "text-warning-500" :
              meta.color === "primary" ? "text-primary-400" :
              "text-foreground/30"
            }`}
          />
        </div>

        {/* Conteúdo */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {event.appName && (
              <span className="text-xs font-semibold text-foreground/80 truncate max-w-[180px]" title={event.appName}>
                {event.appName}
              </span>
            )}
            <Chip size="sm" color={meta.color} variant="flat" className="text-[10px] h-4 px-1.5">
              {meta.label}
            </Chip>
            {event.level === "ERROR" && (
              <Chip size="sm" color="danger" variant="dot" className="text-[10px] h-4">ERR</Chip>
            )}
          </div>

          <p className={`text-xs mt-1 ${LEVEL_COLOR[event.level] || "text-foreground/60"}`}>
            {event.message}
          </p>

          {/* Análise da CyM expandível */}
          {hasDetails && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="flex items-center gap-1 text-[10px] text-primary/60 hover:text-primary mt-1 transition-colors"
            >
              <FontAwesomeIcon icon={expanded ? faChevronUp : faChevronDown} className="w-2.5 h-2.5" />
              {expanded ? "Ocultar análise" : "Ver análise CyM"}
            </button>
          )}

          {expanded && event.aiAnalysis && (
            <div className="mt-2 p-2.5 rounded-lg bg-primary/5 border border-primary/10 text-xs text-foreground/70 whitespace-pre-wrap font-mono leading-relaxed">
              {event.aiAnalysis}
            </div>
          )}

          {expanded && event.details && (
            <div className="mt-2 p-2.5 rounded-lg bg-foreground/5 border border-foreground/10 text-xs text-foreground/50 font-mono">
              {JSON.stringify(event.details, null, 2)}
            </div>
          )}
        </div>

        {/* Ações & timestamp */}
        <div className="shrink-0 text-right">
          <p className="text-[10px] text-foreground/30">{fmtRelative(event.timestamp)}</p>

          {event.action === "WAIT_TOKEN" && onClearToken && event.appId && (
            <button
              onClick={() => onClearToken(event.appId)}
              className="mt-1 text-[10px] text-success-500 hover:text-success-400 underline"
            >
              Token trocado ✓
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Resumo CyM ───────────────────────────────────────────────────────────────

function SummaryPanel({ summary, summaryAt, loading }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] p-5 flex items-center gap-3">
        <Spinner size="sm" />
        <span className="text-sm text-foreground/50">Carregando resumo...</span>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] p-5">
        <div className="flex items-center gap-2 text-foreground/40">
          <FontAwesomeIcon icon={faBrain} className="w-4 h-4" />
          <span className="text-sm">Nenhum resumo gerado ainda. O monitor gera resumos automaticamente a cada ~24 minutos.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/[0.03] p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10">
            <FontAwesomeIcon icon={faBrain} className="w-3.5 h-3.5 text-primary-400" />
          </div>
          <span className="text-sm font-semibold">Análise da CyM</span>
        </div>
        {summaryAt && (
          <span className="text-[10px] text-foreground/30">
            Gerado {fmtRelative(summaryAt)}
          </span>
        )}
      </div>
      <div className="text-sm text-foreground/70 leading-relaxed whitespace-pre-wrap prose prose-sm max-w-none">
        {summary}
      </div>
    </div>
  );
}

// ─── Chat com CyM ─────────────────────────────────────────────────────────────

function CyMChat() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Olá! Sou a CyM. Posso responder perguntas sobre as aplicações monitoradas, analisar padrões de erro, ou ajudar a diagnosticar problemas. O que você quer saber?",
    },
  ]);
  const [input, setInput]     = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const res = await fetch("/api/admin/ai-monitor/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer || "Erro ao obter resposta." },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Erro de conexão com a CyM." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[420px] rounded-xl border border-foreground/10 bg-foreground/[0.02] overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-foreground/10 bg-foreground/[0.03]">
        <div className="w-2 h-2 rounded-full bg-success-500 animate-pulse" />
        <FontAwesomeIcon icon={faBrain} className="w-3.5 h-3.5 text-primary-400" />
        <span className="text-sm font-semibold">Chat com a CyM</span>
        <span className="text-[10px] text-foreground/30 ml-auto">Contexto do monitor incluso automaticamente</span>
      </div>

      {/* Mensagens */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
              msg.role === "user"
                ? "bg-primary/15 text-foreground/90 rounded-br-sm"
                : "bg-foreground/5 text-foreground/80 rounded-bl-sm border border-foreground/5"
            }`}>
              <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-foreground/5 border border-foreground/5 rounded-xl rounded-bl-sm px-3.5 py-2.5 flex items-center gap-2">
              <Spinner size="sm" />
              <span className="text-xs text-foreground/40">CyM analisando...</span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="border-t border-foreground/10 p-3 flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Pergunte sobre as aplicações..."
          disabled={loading}
          className="flex-1 bg-foreground/5 border border-foreground/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-primary/40 transition-colors placeholder:text-foreground/25 disabled:opacity-50"
        />
        <button
          onClick={send}
          disabled={!input.trim() || loading}
          className="p-2 rounded-lg bg-primary/10 text-primary-400 hover:bg-primary/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        >
          <FontAwesomeIcon icon={faPaperPlane} className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ─── App States Grid ──────────────────────────────────────────────────────────

function AppStatesGrid({ appStates }) {
  const entries = Object.entries(appStates || {});

  if (entries.length === 0) {
    return (
      <div className="text-center text-sm text-foreground/40 py-6">
        Nenhuma aplicação monitorada ainda
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
      {entries.map(([dbId, state]) => {
        const isOnline     = ["running", "online"].includes(state.status);
        const waitToken    = state.waitingToken;
        const ramPct       = state.ramUsage?.pctStr;
        const ramCritical  = ramPct && ramPct >= 85;

        return (
          <div
            key={dbId}
            className={`rounded-xl border p-3 transition-all ${
              waitToken    ? "border-danger/30 bg-danger/[0.03]" :
              ramCritical  ? "border-warning/30 bg-warning/[0.03]" :
              isOnline     ? "border-success/15 bg-success/[0.02]" :
              "border-foreground/10 bg-foreground/[0.02]"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  waitToken    ? "bg-danger-500" :
                  ramCritical  ? "bg-warning-500 animate-pulse" :
                  isOnline     ? "bg-success-500" :
                  "bg-foreground/20"
                }`} />
                <span className="text-xs font-semibold text-foreground/80 font-mono truncate max-w-[140px]" title={dbId}>
                  {dbId.slice(-8)}
                </span>
              </div>
              <Chip
                size="sm"
                color={
                  waitToken    ? "danger"  :
                  ramCritical  ? "warning" :
                  isOnline     ? "success" : "default"
                }
                variant="flat"
                className="text-[10px] h-4"
              >
                {waitToken ? "Sem token" : state.status || "—"}
              </Chip>
            </div>

            <div className="space-y-1 text-[10px] text-foreground/40 font-mono">
              {state.lastCheck && (
                <p>Verificado: {fmtRelative(state.lastCheck)}</p>
              )}
              {state.restartCount > 0 && (
                <p className="text-warning-400">Reinicios: {state.restartCount}</p>
              )}
              {state.ramUsage && (
                <div>
                  <div className="flex items-center justify-between mb-0.5">
                    <span className={ramCritical ? "text-warning-400" : ""}>
                      RAM: {state.ramUsage.usedMB}MB / {state.ramUsage.totalMB}MB ({state.ramUsage.pctStr}%)
                    </span>
                  </div>
                  <div className="h-1 rounded-full bg-foreground/10 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        ramCritical ? "bg-warning-500" :
                        state.ramUsage.pctStr > 60 ? "bg-warning-400" :
                        "bg-success-500"
                      }`}
                      style={{ width: `${Math.min(state.ramUsage.pctStr, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function AIMonitorSection() {
  const [state, setState]         = useState(null);
  const [loading, setLoading]     = useState(true);
  const [forcing, setForcing]     = useState(false);
  const [activeTab, setActiveTab] = useState("events");
  const [eventFilter, setEventFilter] = useState("");
  const [logFiles, setLogFiles]   = useState([]);
  const [selectedLog, setSelectedLog] = useState(null);
  const [logContent, setLogContent]   = useState([]);
  const [logLoading, setLogLoading]   = useState(false);
  const refreshRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const res  = await fetch("/api/admin/ai-monitor/state");
      const data = await res.json();
      if (data.success) setState(data);
    } catch {
      // silencioso
    } finally {
      setLoading(false);
    }
  }, []);

  const loadLogFiles = useCallback(async () => {
    try {
      const res  = await fetch("/api/admin/ai-monitor/logs");
      const data = await res.json();
      if (data.success) setLogFiles(data.files || []);
    } catch {}
  }, []);

  const loadLogContent = useCallback(async (filename) => {
    setLogLoading(true);
    setSelectedLog(filename);
    try {
      const res  = await fetch(`/api/admin/ai-monitor/logs/${filename}?limit=300`);
      const data = await res.json();
      if (data.success) setLogContent(data.entries || []);
    } catch {}
    setLogLoading(false);
  }, []);

  const handleForce = async () => {
    setForcing(true);
    try {
      await fetch("/api/admin/ai-monitor/force-cycle", { method: "POST" });
      await load();
    } finally {
      setForcing(false);
    }
  };

  const handleClearToken = async (appId) => {
    try {
      await fetch(`/api/admin/ai-monitor/clear-token/${appId}`, { method: "POST" });
      await load();
    } catch {}
  };

  useEffect(() => {
    load();
    loadLogFiles();
    // Auto-refresh a cada 30s
    refreshRef.current = setInterval(() => { load(); }, 30_000);
    return () => clearInterval(refreshRef.current);
  }, [load, loadLogFiles]);

  useEffect(() => {
    if (activeTab === "logs") loadLogFiles();
  }, [activeTab, loadLogFiles]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  const stats        = state?.stats || {};
  const recentEvents = (state?.recentEvents || [])
    .filter((e) => !eventFilter || e.action === eventFilter || (e.level === eventFilter))
    .reverse();

  const tabs = [
    { id: "events",   label: "Eventos",    icon: faBolt },
    { id: "apps",     label: "Apps",       icon: faServer },
    { id: "summary",  label: "Resumo IA",  icon: faBrain },
    { id: "chat",     label: "Chat CyM",   icon: faBrain },
    { id: "logs",     label: "Logs",       icon: faFileAlt },
  ];

  return (
    <div className="flex flex-col gap-5">

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-primary/10">
            <FontAwesomeIcon icon={faBrain} className="w-5 h-5 text-primary-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold">Monitor Inteligente</h2>
            <p className="text-xs text-foreground/40">
              Powered by CyM · Ciclo #{state?.cycleCount || 0} ·{" "}
              {state?.lastCycle ? `Último: ${fmtRelative(state.lastCycle)}` : "Aguardando..."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Indicador de status */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs border ${
            state?.isRunning
              ? "bg-primary/8 border-primary/20 text-primary-400"
              : "bg-foreground/5 border-foreground/10 text-foreground/50"
          }`}>
            <div className={`w-1.5 h-1.5 rounded-full ${
              state?.isRunning ? "bg-primary-400 animate-pulse" : "bg-foreground/30"
            }`} />
            {state?.isRunning ? "Executando..." : "Em espera"}
          </div>

          <Button
            size="sm"
            variant="flat"
            onPress={load}
            isIconOnly
            className="text-foreground/50"
          >
            <FontAwesomeIcon icon={faArrowsRotate} className="w-3.5 h-3.5" />
          </Button>

          <Button
            size="sm"
            color="primary"
            variant="flat"
            onPress={handleForce}
            isLoading={forcing}
            startContent={!forcing && <FontAwesomeIcon icon={faRotate} className="w-3 h-3" />}
          >
            Forçar ciclo
          </Button>
        </div>
      </div>

      {/* ── Stats ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          icon={faServer}
          label="Apps monitoradas"
          value={stats.total ?? 0}
          accent="border-foreground/10"
          sub={`${state?.cycleCount || 0} ciclos`}
        />
        <StatCard
          icon={faRotate}
          label="Reinicios feitos"
          value={stats.restarted ?? 0}
          accent="border-success/15"
          sub="pela IA"
        />
        <StatCard
          icon={faKey}
          label="Sem token"
          value={stats.waitingToken ?? 0}
          accent="border-danger/15"
          sub="aguardando dono"
        />
        <StatCard
          icon={faExclamationTriangle}
          label="Erros"
          value={stats.errors ?? 0}
          accent="border-warning/15"
          sub="registrados"
        />
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1 border-b border-foreground/10 pb-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-t-lg transition-all ${
              activeTab === tab.id
                ? "bg-foreground/5 text-foreground border-b-2 border-primary-400 -mb-px"
                : "text-foreground/50 hover:text-foreground/80"
            }`}
          >
            <FontAwesomeIcon icon={tab.icon} className="w-3 h-3" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Eventos ── */}
      {activeTab === "events" && (
        <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] overflow-hidden">
          {/* Filtros */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-foreground/10 flex-wrap">
            <FontAwesomeIcon icon={faFilter} className="w-3 h-3 text-foreground/30" />
            {["", "RESTARTED", "WAIT_TOKEN", "ERROR", "REPORT_ONLY", "RESTART_RAM"].map((f) => (
              <button
                key={f}
                onClick={() => setEventFilter(f)}
                className={`text-[10px] px-2 py-1 rounded-full border transition-all ${
                  eventFilter === f
                    ? "bg-primary/15 border-primary/30 text-primary-400"
                    : "border-foreground/10 text-foreground/40 hover:text-foreground/60"
                }`}
              >
                {f || "Todos"}
              </button>
            ))}
            <span className="ml-auto text-[10px] text-foreground/30">
              {recentEvents.length} evento(s)
            </span>
          </div>

          {/* Feed */}
          <div className="max-h-[500px] overflow-y-auto">
            {recentEvents.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-foreground/30 gap-2">
                <FontAwesomeIcon icon={faBolt} className="w-8 h-8 opacity-20" />
                <p className="text-sm">Nenhum evento registrado</p>
              </div>
            ) : (
              recentEvents.map((event, i) => (
                <EventRow key={i} event={event} onClearToken={handleClearToken} />
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Tab: Apps ── */}
      {activeTab === "apps" && (
        <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] p-4">
          <AppStatesGrid appStates={state?.appStates || {}} />
        </div>
      )}

      {/* ── Tab: Resumo ── */}
      {activeTab === "summary" && (
        <SummaryPanel
          summary={state?.summary}
          summaryAt={state?.summaryAt}
          loading={false}
        />
      )}

      {/* ── Tab: Chat ── */}
      {activeTab === "chat" && <CyMChat />}

      {/* ── Tab: Logs ── */}
      {activeTab === "logs" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Lista de arquivos */}
          <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] overflow-hidden">
            <div className="px-4 py-3 border-b border-foreground/10 text-xs font-semibold text-foreground/50">
              Arquivos de log
            </div>
            <div className="max-h-[400px] overflow-y-auto">
              {logFiles.length === 0 ? (
                <div className="p-4 text-sm text-foreground/30 text-center">
                  Nenhum arquivo de log
                </div>
              ) : (
                logFiles.map((f) => (
                  <button
                    key={f.name}
                    onClick={() => loadLogContent(f.name)}
                    className={`w-full flex items-center justify-between px-4 py-2.5 hover:bg-foreground/5 transition-colors border-b border-foreground/5 last:border-0 ${
                      selectedLog === f.name ? "bg-primary/8" : ""
                    }`}
                  >
                    <div className="text-left">
                      <p className="text-xs font-medium">{f.date}</p>
                      <p className="text-[10px] text-foreground/30">
                        {(f.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    <FontAwesomeIcon icon={faFileAlt} className="w-3 h-3 text-foreground/20" />
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Conteúdo do log */}
          <div className="md:col-span-2 rounded-xl border border-foreground/10 bg-foreground/[0.02] overflow-hidden">
            <div className="px-4 py-3 border-b border-foreground/10 text-xs font-semibold text-foreground/50">
              {selectedLog || "Selecione um arquivo"}
            </div>

            {logLoading ? (
              <div className="flex items-center justify-center h-40">
                <Spinner size="sm" />
              </div>
            ) : logContent.length === 0 ? (
              <div className="p-4 text-sm text-foreground/30 text-center">
                {selectedLog ? "Arquivo vazio" : "Selecione um arquivo para visualizar"}
              </div>
            ) : (
              <div className="max-h-[400px] overflow-y-auto">
                {logContent.map((entry, i) => (
                  <div
                    key={i}
                    className={`px-4 py-2 border-b border-foreground/5 last:border-0 text-[10px] font-mono ${
                      entry.level === "ERROR"   ? "bg-danger/[0.02] text-danger-400" :
                      entry.level === "WARN"    ? "bg-warning/[0.02] text-warning-400" :
                      entry.level === "SUMMARY" ? "bg-primary/[0.02] text-primary-400" :
                      "text-foreground/50"
                    }`}
                  >
                    <span className="text-foreground/30 mr-2">{entry.timestamp?.slice(11, 19)}</span>
                    <span className="mr-2 font-semibold">[{entry.level || "—"}]</span>
                    <span>{entry.message || entry.raw || JSON.stringify(entry)}</span>
                    {entry.appName && (
                      <span className="ml-2 text-foreground/30">({entry.appName})</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}