"use client";

/**
 * src/app/dashboard/admin/sections/divulgacao/section.tsx
 *
 * Seção de Divulgação no painel admin.
 * Tabs: Tokens · Canais · Logs
 * (Mensagem agora é editada diretamente no topo da seção)
 */

import { useEffect, useState, useRef, useCallback } from "react";
import {
  Button,
  Input,
  Switch,
  Spinner,
  Chip,
  Tabs,
  Tab,
  Textarea,
  Tooltip,
} from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBullhorn,
  faPlus,
  faTrash,
  faRotate,
  faCheckCircle,
  faTimesCircle,
  faPlay,
  faStop,
  faCopy,
  faFloppyDisk,
  faPaperPlane,
  faMagnifyingGlass,
  faCircleInfo,
  faLink,
  faHashtag,
  faUser,
  faKey,
  faClock,
  faArrowRightArrowLeft,
  faCircleDot,
  faTriangleExclamation,
} from "@fortawesome/free-solid-svg-icons";
import { SectionHeader } from "@/components/layout/SectionHeader";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ChannelConfig {
  channelId: string;
  channelName: string;
  guildId: string;
  guildName: string;
  slowmode: number;
  lastSentAt: string | null;
  enabled: boolean;
}

interface TokenConfig {
  id: string;
  label: string;
  token: string;
  isValid: boolean | null;
  lastValidatedAt: string | null;
  username: string | null;
  userId: string | null;
  avatar: string | null;
  channels: ChannelConfig[];
  isActive: boolean;
}

interface DivulgacaoConfig {
  _id: string;
  message: string;
  tokens: TokenConfig[];
  isRunning: boolean;
  totalSent: number;
  totalErrors: number;
  startedAt: string | null;
  updatedAt: string;
}

interface LogEntry {
  ts: string;
  level: "info" | "warn" | "error" | "success";
  token: string;
  channel: string;
  msg: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const API = "/api/admin/divulgacao";

async function apiFetch(path: string, opts?: RequestInit) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });

  const contentType = res.headers.get("content-type") || "";
  let data: any = {};
  if (contentType.includes("application/json")) {
    try {
      data = await res.json();
    } catch {
      throw new Error(`Resposta inválida do servidor (HTTP ${res.status})`);
    }
  } else if (!res.ok) {
    // Servidor retornou HTML ou texto de erro (ex: crash, proxy 502)
    const text = await res.text().catch(() => "");
    throw new Error(`Erro HTTP ${res.status}${text ? `: ${text.slice(0, 120)}` : ""}`);
  }

  if (!res.ok) throw new Error(data.error || `Erro na requisição (HTTP ${res.status})`);
  return data;
}

function slowmodeLabel(s: number) {
  if (s === 0) return "Sem slowmode";
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}min`;
  return `${Math.floor(s / 3600)}h`;
}

// ─── TokenCard ────────────────────────────────────────────────────────────────

function TokenCard({
  token,
  onDelete,
  onToggle,
  onValidate,
  onLabelChange,
  onRotate,
}: {
  token: TokenConfig;
  onDelete: () => void;
  onToggle: (v: boolean) => void;
  onValidate: () => void;
  onLabelChange: (label: string) => void;
  onRotate: () => void;
}) {
  const [editLabel, setEditLabel] = useState(false);
  const [label, setLabel] = useState(token.label);
  const [savingLabel, setSavingLabel] = useState(false);
  const [validating, setValidating] = useState(false);

  const saveLabel = async () => {
    setSavingLabel(true);
    try {
      await apiFetch(`/tokens/${token.id}`, {
        method: "PATCH",
        body: JSON.stringify({ label }),
      });
      onLabelChange(label);
    } catch {}
    setSavingLabel(false);
    setEditLabel(false);
  };

  const handleValidate = async () => {
    setValidating(true);
    await onValidate();
    setValidating(false);
  };

  return (
    <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start gap-3">
        {token.avatar ? (
          <img
            src={token.avatar}
            alt={token.username || "conta"}
            className="w-10 h-10 rounded-full border border-foreground/10 shrink-0"
          />
        ) : (
          <div className="w-10 h-10 rounded-full bg-foreground/10 flex items-center justify-center shrink-0">
            <FontAwesomeIcon icon={faUser} className="text-foreground/40" />
          </div>
        )}

        <div className="flex-1 min-w-0">
          {editLabel ? (
            <div className="flex items-center gap-2">
              <input
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                className="flex-1 bg-foreground/8 border border-foreground/15 rounded-lg px-2 py-1 text-sm outline-none focus:border-primary/50"
                autoFocus
                onKeyDown={(e) => e.key === "Enter" && saveLabel()}
              />
              <button
                onClick={saveLabel}
                disabled={savingLabel}
                className="px-2 py-1 rounded bg-primary/20 text-primary text-xs hover:bg-primary/30 transition-colors"
              >
                {savingLabel ? "..." : "OK"}
              </button>
              <button
                onClick={() => setEditLabel(false)}
                className="px-2 py-1 rounded bg-foreground/8 text-foreground/50 text-xs hover:bg-foreground/15"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditLabel(true)}
              className="text-sm font-semibold hover:text-primary transition-colors text-left"
            >
              {token.label || token.username || "Sem nome"}
            </button>
          )}
          <p className="text-xs text-foreground/50 mt-0.5 font-mono">
            {token.token}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {token.isValid === true && (
            <Chip size="sm" color="success" variant="flat">
              Válido
            </Chip>
          )}
          {token.isValid === false && (
            <Chip size="sm" color="danger" variant="flat">
              Inválido
            </Chip>
          )}
          {token.isValid === null && (
            <Chip size="sm" color="default" variant="flat">
              Não verificado
            </Chip>
          )}

          <Switch
            size="sm"
            isSelected={token.isActive}
            onValueChange={onToggle}
          />
        </div>
      </div>

      {/* Info */}
      <div className="flex items-center gap-4 text-xs text-foreground/50">
        {token.userId && (
          <span className="flex items-center gap-1">
            <FontAwesomeIcon icon={faUser} className="text-[10px]" />
            {token.username}
          </span>
        )}
        <span className="flex items-center gap-1">
          <FontAwesomeIcon icon={faHashtag} className="text-[10px]" />
          {token.channels.length} canal(is)
        </span>
        {token.lastValidatedAt && (
          <span className="flex items-center gap-1">
            <FontAwesomeIcon icon={faClock} className="text-[10px]" />
            Verificado {new Date(token.lastValidatedAt).toLocaleDateString("pt-BR")}
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1 border-t border-foreground/8">
        <button
          onClick={handleValidate}
          disabled={validating}
          className="flex items-center gap-1.5 text-xs text-foreground/50 hover:text-primary transition-colors"
        >
          <FontAwesomeIcon
            icon={faRotate}
            className={`text-[10px] ${validating ? "animate-spin" : ""}`}
          />
          Validar
        </button>

        <button
          onClick={onRotate}
          className="flex items-center gap-1.5 text-xs text-foreground/50 hover:text-warning transition-colors"
        >
          <FontAwesomeIcon icon={faKey} className="text-[10px]" />
          Trocar token
        </button>

        <button
          onClick={onDelete}
          className="flex items-center gap-1.5 text-xs text-foreground/50 hover:text-danger transition-colors ml-auto"
        >
          <FontAwesomeIcon icon={faTrash} className="text-[10px]" />
          Remover
        </button>
      </div>
    </div>
  );
}

// ─── ChannelRow ───────────────────────────────────────────────────────────────

function ChannelRow({
  ch,
  tokenId,
  onDelete,
  onToggle,
  onSlowmodeChange,
  onTest,
}: {
  ch: ChannelConfig;
  tokenId: string;
  onDelete: () => void;
  onToggle: (v: boolean) => void;
  onSlowmodeChange: (v: number) => void;
  onTest: () => void;
}) {
  const [testing, setTesting] = useState(false);
  const [slowmodeEdit, setSlowmodeEdit] = useState(false);
  const [slowmodeVal, setSlowmodeVal] = useState(String(ch.slowmode));

  const handleTest = async () => {
    setTesting(true);
    await onTest();
    setTesting(false);
  };

  const saveSlowmode = () => {
    const v = Number(slowmodeVal);
    if (!isNaN(v) && v >= 0) onSlowmodeChange(v);
    setSlowmodeEdit(false);
  };

  return (
    <div
      className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border transition-colors ${
        ch.enabled
          ? "border-foreground/10 bg-foreground/[0.02]"
          : "border-foreground/5 bg-transparent opacity-50"
      }`}
    >
      <FontAwesomeIcon icon={faHashtag} className="text-foreground/30 text-xs shrink-0" />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{ch.channelName || ch.channelId}</p>
        <p className="text-xs text-foreground/40 font-mono">{ch.channelId}</p>
      </div>

      {/* Slowmode badge */}
      <div
        onClick={() => setSlowmodeEdit(true)}
        className="cursor-pointer"
      >
        {slowmodeEdit ? (
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <input
              value={slowmodeVal}
              onChange={(e) => setSlowmodeVal(e.target.value)}
              className="w-16 bg-foreground/10 border border-foreground/20 rounded px-1.5 py-0.5 text-xs font-mono outline-none"
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && saveSlowmode()}
            />
            <span className="text-xs text-foreground/40">s</span>
            <button onClick={saveSlowmode} className="text-xs text-primary">OK</button>
          </div>
        ) : (
          <Chip
            size="sm"
            color={ch.slowmode > 0 ? "warning" : "default"}
            variant="flat"
            className="cursor-pointer"
          >
            {slowmodeLabel(ch.slowmode)}
          </Chip>
        )}
      </div>

      {ch.lastSentAt && (
        <span className="text-xs text-foreground/30 hidden sm:block">
          {new Date(ch.lastSentAt).toLocaleTimeString("pt-BR")}
        </span>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 shrink-0">
        <Tooltip content="Enviar teste">
          <button
            onClick={handleTest}
            disabled={testing}
            className="w-7 h-7 flex items-center justify-center rounded-lg bg-foreground/5 hover:bg-primary/15 hover:text-primary text-foreground/40 transition-colors"
          >
            <FontAwesomeIcon
              icon={testing ? faRotate : faPaperPlane}
              className={`text-xs ${testing ? "animate-spin" : ""}`}
            />
          </button>
        </Tooltip>

        <Switch size="sm" isSelected={ch.enabled} onValueChange={onToggle} />

        <button
          onClick={onDelete}
          className="w-7 h-7 flex items-center justify-center rounded-lg bg-foreground/5 hover:bg-danger/15 hover:text-danger text-foreground/40 transition-colors"
        >
          <FontAwesomeIcon icon={faTrash} className="text-xs" />
        </button>
      </div>
    </div>
  );
}

// ─── CopyChannelsModal ────────────────────────────────────────────────────────

function CopyChannelsModal({
  tokens,
  sourceId,
  onClose,
  onSuccess,
}: {
  tokens: TokenConfig[];
  sourceId: string;
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const [destId, setDestId] = useState("");
  const [overwrite, setOverwrite] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const source = tokens.find((t) => t.id === sourceId);
  const targets = tokens.filter((t) => t.id !== sourceId);

  const handleCopy = async () => {
    if (!destId) return;
    setLoading(true);
    try {
      const data = await apiFetch(
        `/tokens/${sourceId}/copy-channels/${destId}`,
        {
          method: "POST",
          body: JSON.stringify({ overwrite }),
        }
      );
      setResult(data.message);
      onSuccess(data.message);
    } catch (err: any) {
      setResult(`Erro: ${err.message}`);
    }
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md bg-background border border-foreground/15 rounded-2xl p-6 shadow-2xl">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-xl bg-primary/15 flex items-center justify-center">
            <FontAwesomeIcon icon={faArrowRightArrowLeft} className="text-primary text-sm" />
          </div>
          <div>
            <h3 className="font-semibold">Copiar Configuração de Canais</h3>
            <p className="text-xs text-foreground/50">
              De: <strong>{source?.label || source?.username}</strong>
            </p>
          </div>
          <button onClick={onClose} className="ml-auto text-foreground/40 hover:text-foreground">✕</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-foreground/60 mb-1.5 block">
              Copiar para
            </label>
            <select
              value={destId}
              onChange={(e) => setDestId(e.target.value)}
              className="w-full bg-foreground/5 border border-foreground/15 rounded-lg px-3 py-2 text-sm outline-none focus:border-primary/50"
            >
              <option value="">Selecione o token de destino</option>
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label || t.username || t.token}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg bg-warning/8 border border-warning/20">
            <div>
              <p className="text-sm font-medium">Sobrescrever canais existentes</p>
              <p className="text-xs text-foreground/50 mt-0.5">
                Se desativado, apenas adiciona canais que não existem no destino
              </p>
            </div>
            <Switch size="sm" isSelected={overwrite} onValueChange={setOverwrite} />
          </div>

          {result && (
            <div className="text-xs p-3 rounded-lg bg-success/10 border border-success/20 text-success-700">
              {result}
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <Button variant="light" size="sm" onPress={onClose} className="flex-1">
              Fechar
            </Button>
            <Button
              color="primary"
              size="sm"
              onPress={handleCopy}
              isDisabled={!destId || loading}
              isLoading={loading}
              className="flex-1"
              startContent={<FontAwesomeIcon icon={faCopy} />}
            >
              Copiar
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── RotateTokenModal ─────────────────────────────────────────────────────────

function RotateTokenModal({
  token,
  onClose,
  onSuccess,
}: {
  token: TokenConfig;
  onClose: () => void;
  onSuccess: (tokenId: string, newData: Partial<TokenConfig>) => void;
}) {
  const [newToken, setNewToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!newToken.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch(`/tokens/${token.id}/rotate-token`, {
        method: "POST",
        body: JSON.stringify({ newToken: newToken.trim() }),
      });
      onSuccess(token.id, {
        token: data.token ?? token.token,
        isValid: true,
        username: data.username ?? token.username,
        userId: data.userId ?? token.userId,
        avatar: data.avatar ?? token.avatar,
        lastValidatedAt: new Date().toISOString(),
      });
      onClose();
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md bg-background border border-foreground/15 rounded-2xl p-6 shadow-2xl">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-xl bg-warning/15 flex items-center justify-center">
            <FontAwesomeIcon icon={faKey} className="text-warning text-sm" />
          </div>
          <div>
            <h3 className="font-semibold">Trocar Token</h3>
            <p className="text-xs text-foreground/50">
              Conta: <strong>{token.label || token.username}</strong>
            </p>
          </div>
          <button onClick={onClose} className="ml-auto text-foreground/40 hover:text-foreground">✕</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-foreground/60 mb-1.5 block">
              Token atual (mascarado)
            </label>
            <p className="text-xs font-mono text-foreground/40 bg-foreground/5 rounded-lg px-3 py-2">
              {token.token}
            </p>
          </div>

          <div>
            <label className="text-xs font-medium text-foreground/60 mb-1.5 block">
              Novo token
            </label>
            <Input
              size="sm"
              placeholder="Cole o novo token aqui"
              value={newToken}
              onChange={(e) => setNewToken(e.target.value)}
              startContent={<FontAwesomeIcon icon={faKey} className="text-foreground/30 text-xs" />}
              type="password"
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-xs p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger">
              <FontAwesomeIcon icon={faTriangleExclamation} className="shrink-0" />
              {error}
            </div>
          )}

          <p className="text-xs text-foreground/40 flex items-center gap-1.5">
            <FontAwesomeIcon icon={faCircleInfo} className="text-[10px]" />
            O novo token será validado no Discord antes de ser salvo. Os canais configurados são mantidos.
          </p>

          <div className="flex gap-2 pt-1">
            <Button variant="light" size="sm" onPress={onClose} className="flex-1">
              Cancelar
            </Button>
            <Button
              color="warning"
              size="sm"
              onPress={handleSubmit}
              isDisabled={!newToken.trim() || loading}
              isLoading={loading}
              className="flex-1"
              startContent={!loading && <FontAwesomeIcon icon={faRotate} />}
            >
              Trocar Token
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main Section ─────────────────────────────────────────────────────────────

export function DivulgacaoSection() {
  const [config, setConfig] = useState<DivulgacaoConfig | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const logsRef = useRef<HTMLDivElement>(null);

  // Add token
  const [newToken, setNewToken] = useState("");
  const [newTokenLabel, setNewTokenLabel] = useState("");
  const [addingToken, setAddingToken] = useState(false);

  // Add channel
  const [selectedTokenId, setSelectedTokenId] = useState<string>("");
  const [newChannelId, setNewChannelId] = useState("");
  const [addingChannel, setAddingChannel] = useState(false);

  // Copy channels modal
  const [copyModalSourceId, setCopyModalSourceId] = useState<string | null>(null);

  // Rotate token modal
  const [rotateModalToken, setRotateModalToken] = useState<TokenConfig | null>(null);

  // Message (única, sem embed)
  const [message, setMessage] = useState("");
  const [savingMessage, setSavingMessage] = useState(false);
  const [messageChanged, setMessageChanged] = useState(false);

  const showToast = (type: "success" | "error", msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3500);
  };

  const loadConfig = useCallback(async () => {
    try {
      const data = await apiFetch("/");
      setConfig(data.config);
      setIsRunning(data.isRunning);
      setMessage(data.config.message || "");
    } catch (err: any) {
      showToast("error", err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const data = await apiFetch("/logs?limit=100");
      setLogs(data.logs || []);
      setIsRunning(data.isRunning);
    } catch {}
    setLogsLoading(false);
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  // Auto-refresh logs quando rodando
  useEffect(() => {
    if (!isRunning) return;
    const interval = setInterval(loadLogs, 3000);
    return () => clearInterval(interval);
  }, [isRunning, loadLogs]);

  // ── Tokens ─────────────────────────────────────────────────────────────────

  const handleAddToken = async () => {
    if (!newToken.trim()) return;
    setAddingToken(true);
    try {
      const data = await apiFetch("/tokens", {
        method: "POST",
        body: JSON.stringify({ token: newToken.trim(), label: newTokenLabel.trim() }),
      });
      setConfig((prev) =>
        prev ? { ...prev, tokens: [...prev.tokens, data.token] } : prev
      );
      setNewToken("");
      setNewTokenLabel("");
      showToast("success", `Token ${data.token.label || data.token.username} adicionado!`);
    } catch (err: any) {
      showToast("error", err.message);
    }
    setAddingToken(false);
  };

  const handleDeleteToken = async (tokenId: string) => {
    if (!confirm("Remover este token?")) return;
    try {
      await apiFetch(`/tokens/${tokenId}`, { method: "DELETE" });
      setConfig((prev) =>
        prev ? { ...prev, tokens: prev.tokens.filter((t) => t.id !== tokenId) } : prev
      );
      showToast("success", "Token removido");
    } catch (err: any) {
      showToast("error", err.message);
    }
  };

  const handleToggleToken = async (tokenId: string, isActive: boolean) => {
    try {
      await apiFetch(`/tokens/${tokenId}`, {
        method: "PATCH",
        body: JSON.stringify({ isActive }),
      });
      setConfig((prev) =>
        prev
          ? {
              ...prev,
              tokens: prev.tokens.map((t) =>
                t.id === tokenId ? { ...t, isActive } : t
              ),
            }
          : prev
      );
    } catch (err: any) {
      showToast("error", err.message);
    }
  };

  const handleValidateToken = async (tokenId: string) => {
    try {
      const data = await apiFetch(`/tokens/${tokenId}/validate`, {
        method: "POST",
      });
      setConfig((prev) =>
        prev
          ? {
              ...prev,
              tokens: prev.tokens.map((t) =>
                t.id === tokenId
                  ? {
                      ...t,
                      isValid: data.valid,
                      username: data.username || t.username,
                      avatar: data.avatar || t.avatar,
                      lastValidatedAt: new Date().toISOString(),
                    }
                  : t
              ),
            }
          : prev
      );
      showToast(data.valid ? "success" : "error", data.valid ? "Token válido!" : "Token inválido");
    } catch (err: any) {
      showToast("error", err.message);
    }
  };

  const handleRotateToken = (tokenId: string, newData: Partial<TokenConfig>) => {
    setConfig((prev) =>
      prev
        ? {
            ...prev,
            tokens: prev.tokens.map((t) =>
              t.id === tokenId ? { ...t, ...newData } : t
            ),
          }
        : prev
    );
    showToast("success", "Token trocado com sucesso!");
  };

  // ── Channels ───────────────────────────────────────────────────────────────

  const handleAddChannel = async () => {
    if (!selectedTokenId || !newChannelId.trim()) return;
    setAddingChannel(true);
    try {
      const data = await apiFetch(`/tokens/${selectedTokenId}/channels`, {
        method: "POST",
        body: JSON.stringify({ channelId: newChannelId.trim() }),
      });
      setConfig((prev) =>
        prev
          ? {
              ...prev,
              tokens: prev.tokens.map((t) =>
                t.id === selectedTokenId
                  ? { ...t, channels: [...t.channels, data.channel] }
                  : t
              ),
            }
          : prev
      );
      setNewChannelId("");
      showToast("success", `Canal ${data.channel.channelName} adicionado!`);
    } catch (err: any) {
      showToast("error", err.message);
    }
    setAddingChannel(false);
  };

  const handleDeleteChannel = async (tokenId: string, channelId: string) => {
    try {
      await apiFetch(`/tokens/${tokenId}/channels/${channelId}`, {
        method: "DELETE",
      });
      setConfig((prev) =>
        prev
          ? {
              ...prev,
              tokens: prev.tokens.map((t) =>
                t.id === tokenId
                  ? { ...t, channels: t.channels.filter((c) => c.channelId !== channelId) }
                  : t
              ),
            }
          : prev
      );
    } catch (err: any) {
      showToast("error", err.message);
    }
  };

  const handleToggleChannel = async (tokenId: string, channelId: string, enabled: boolean) => {
    try {
      await apiFetch(`/tokens/${tokenId}/channels/${channelId}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      });
      setConfig((prev) =>
        prev
          ? {
              ...prev,
              tokens: prev.tokens.map((t) =>
                t.id === tokenId
                  ? {
                      ...t,
                      channels: t.channels.map((c) =>
                        c.channelId === channelId ? { ...c, enabled } : c
                      ),
                    }
                  : t
              ),
            }
          : prev
      );
    } catch (err: any) {
      showToast("error", err.message);
    }
  };

  const handleSlowmodeChange = async (tokenId: string, channelId: string, slowmode: number) => {
    try {
      await apiFetch(`/tokens/${tokenId}/channels/${channelId}`, {
        method: "PATCH",
        body: JSON.stringify({ slowmode }),
      });
      setConfig((prev) =>
        prev
          ? {
              ...prev,
              tokens: prev.tokens.map((t) =>
                t.id === tokenId
                  ? {
                      ...t,
                      channels: t.channels.map((c) =>
                        c.channelId === channelId ? { ...c, slowmode } : c
                      ),
                    }
                  : t
              ),
            }
          : prev
      );
      showToast("success", "Slowmode atualizado");
    } catch (err: any) {
      showToast("error", err.message);
    }
  };

  const handleTestChannel = async (tokenId: string, channelId: string) => {
    try {
      const data = await apiFetch(`/tokens/${tokenId}/channels/${channelId}/test`, {
        method: "POST",
      });
      showToast("success", data.message || "Mensagem de teste enviada!");
    } catch (err: any) {
      showToast("error", err.message);
    }
  };

  // ── Message ────────────────────────────────────────────────────────────────

  const handleSaveMessage = async () => {
    setSavingMessage(true);
    try {
      await apiFetch("/message", {
        method: "PUT",
        body: JSON.stringify({ message }),
      });
      setMessageChanged(false);
      showToast("success", "Mensagem salva!");
    } catch (err: any) {
      showToast("error", err.message);
    }
    setSavingMessage(false);
  };

  // ── Start / Stop ───────────────────────────────────────────────────────────

  const handleStartStop = async () => {
    setActionLoading(true);
    try {
      if (isRunning) {
        await apiFetch("/stop", { method: "POST" });
        setIsRunning(false);
        showToast("success", "Serviço parado");
      } else {
        await apiFetch("/start", { method: "POST" });
        setIsRunning(true);
        showToast("success", "Serviço iniciado!");
        loadLogs();
      }
    } catch (err: any) {
      showToast("error", err.message);
    }
    setActionLoading(false);
  };

  // ─── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  const tokens = config?.tokens ?? [];
  const totalChannels = tokens.reduce((s, t) => s + t.channels.length, 0);

  return (
    <div className="flex flex-col gap-5">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-5 right-5 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-xl text-sm font-medium transition-all ${
            toast.type === "success"
              ? "bg-success/15 border-success/25 text-success-700"
              : "bg-danger/15 border-danger/25 text-danger-600"
          }`}
        >
          <FontAwesomeIcon
            icon={toast.type === "success" ? faCheckCircle : faTimesCircle}
            className="text-xs"
          />
          {toast.msg}
        </div>
      )}

      {/* Rotate Token Modal */}
      {rotateModalToken && (
        <RotateTokenModal
          token={rotateModalToken}
          onClose={() => setRotateModalToken(null)}
          onSuccess={handleRotateToken}
        />
      )}

      {/* Copy Modal */}
      {copyModalSourceId && (
        <CopyChannelsModal
          tokens={tokens}
          sourceId={copyModalSourceId}
          onClose={() => setCopyModalSourceId(null)}
          onSuccess={(msg) => {
            showToast("success", msg);
            loadConfig();
            setCopyModalSourceId(null);
          }}
        />
      )}

      {/* Header */}
      <SectionHeader
        description="Configure e gerencie o envio automatizado de mensagens de divulgação"
        actions={
          <div className="flex items-center gap-3">
            {/* Stats */}
            {config && (
              <div className="hidden md:flex items-center gap-4 text-xs text-foreground/50">
                <span>{tokens.length} token(s)</span>
                <span>{totalChannels} canal(is)</span>
                <span className="text-success">{config.totalSent} enviados</span>
                {config.totalErrors > 0 && (
                  <span className="text-danger">{config.totalErrors} erros</span>
                )}
              </div>
            )}

            <Button
              size="sm"
              variant="light"
              onPress={loadConfig}
              startContent={<FontAwesomeIcon icon={faRotate} />}
            >
              Atualizar
            </Button>

            {/* Start/Stop */}
            <Button
              size="sm"
              color={isRunning ? "danger" : "success"}
              variant={isRunning ? "flat" : "solid"}
              onPress={handleStartStop}
              isLoading={actionLoading}
              startContent={
                <FontAwesomeIcon icon={isRunning ? faStop : faPlay} />
              }
            >
              {isRunning ? "Parar" : "Iniciar"}
            </Button>
          </div>
        }
      />

      {/* Status bar */}
      <div
        className={`flex items-center gap-3 px-4 py-3 rounded-xl border text-sm ${
          isRunning
            ? "bg-success/8 border-success/20"
            : "bg-foreground/5 border-foreground/10"
        }`}
      >
        <div
          className={`w-2 h-2 rounded-full ${
            isRunning ? "bg-success animate-pulse" : "bg-foreground/20"
          }`}
        />
        <span className={isRunning ? "text-success-700 font-medium" : "text-foreground/50"}>
          {isRunning ? "Serviço ativo — enviando mensagens" : "Serviço inativo"}
        </span>
        {config?.startedAt && isRunning && (
          <span className="text-foreground/40 text-xs ml-auto">
            Iniciado em {new Date(config.startedAt).toLocaleString("pt-BR")}
          </span>
        )}
      </div>

      {/* Message Editor (único, sem embed) */}
      <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] p-4 space-y-3">
        <p className="text-sm font-semibold">Mensagem de Divulgação</p>
        <Textarea
          placeholder="Digite a mensagem que será enviada..."
          value={message}
          onChange={(e) => {
            setMessage(e.target.value);
            setMessageChanged(true);
          }}
          minRows={4}
          maxRows={10}
          className="font-mono text-sm"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-foreground/40">{message.length} caracteres</span>
          <Button
            size="sm"
            color="primary"
            onPress={handleSaveMessage}
            isLoading={savingMessage}
            isDisabled={!messageChanged}
            startContent={<FontAwesomeIcon icon={faFloppyDisk} />}
          >
            Salvar Mensagem
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs aria-label="Divulgação" variant="underlined" size="sm">
        {/* ── Tab: Tokens ───────────────────────────────────────────────────── */}
        <Tab
          key="tokens"
          title={
            <span className="flex items-center gap-2">
              <FontAwesomeIcon icon={faKey} />
              Tokens ({tokens.length})
            </span>
          }
        >
          <div className="space-y-4 mt-3">
            {/* Add token form */}
            <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] p-4 space-y-3">
              <p className="text-sm font-semibold">Adicionar Token de Conta</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <Input
                  size="sm"
                  placeholder="Token da conta Discord"
                  value={newToken}
                  onChange={(e) => setNewToken(e.target.value)}
                  type="password"
                  startContent={<FontAwesomeIcon icon={faKey} className="text-foreground/30 text-xs" />}
                  className="sm:col-span-2"
                />
                <Input
                  size="sm"
                  placeholder="Apelido (opcional)"
                  value={newTokenLabel}
                  onChange={(e) => setNewTokenLabel(e.target.value)}
                />
              </div>
              <p className="text-xs text-foreground/40 flex items-center gap-1.5">
                <FontAwesomeIcon icon={faCircleInfo} className="text-[10px]" />
                Insira o token de uma conta Discord (não bot). O token será validado ao adicionar.
              </p>
              <Button
                size="sm"
                color="primary"
                onPress={handleAddToken}
                isLoading={addingToken}
                isDisabled={!newToken.trim()}
                startContent={<FontAwesomeIcon icon={faPlus} />}
              >
                Adicionar Token
              </Button>
            </div>

            {/* Token list */}
            {tokens.length === 0 ? (
              <div className="rounded-xl border border-dashed border-foreground/15 p-8 text-center">
                <FontAwesomeIcon icon={faKey} className="text-foreground/20 text-2xl mb-2" />
                <p className="text-sm text-foreground/50">Nenhum token cadastrado</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {tokens.map((token) => (
                  <div key={token.id} className="relative group">
                    <TokenCard
                      token={token}
                      onDelete={() => handleDeleteToken(token.id)}
                      onToggle={(v) => handleToggleToken(token.id, v)}
                      onValidate={() => handleValidateToken(token.id)}
                      onLabelChange={(label) =>
                        setConfig((prev) =>
                          prev
                            ? {
                                ...prev,
                                tokens: prev.tokens.map((t) =>
                                  t.id === token.id ? { ...t, label } : t
                                ),
                              }
                            : prev
                        )
                      }
                      onRotate={() => setRotateModalToken(token)}
                    />
                    {tokens.length > 1 && (
                      <button
                        onClick={() => setCopyModalSourceId(token.id)}
                        className="absolute top-3 right-14 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-xs text-foreground/40 hover:text-primary px-2 py-1 rounded bg-foreground/5"
                      >
                        <FontAwesomeIcon icon={faArrowRightArrowLeft} className="text-[10px]" />
                        Copiar canais
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </Tab>

        {/* ── Tab: Canais ───────────────────────────────────────────────────── */}
        <Tab
          key="channels"
          title={
            <span className="flex items-center gap-2">
              <FontAwesomeIcon icon={faHashtag} />
              Canais ({totalChannels})
            </span>
          }
        >
          <div className="space-y-5 mt-3">
            {/* Add channel form */}
            <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] p-4 space-y-3">
              <p className="text-sm font-semibold">Adicionar Canal</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <select
                  value={selectedTokenId}
                  onChange={(e) => setSelectedTokenId(e.target.value)}
                  className="bg-foreground/5 border border-foreground/15 rounded-lg px-3 py-2 text-sm outline-none focus:border-primary/50"
                >
                  <option value="">Selecionar token</option>
                  {tokens.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.label || t.username || t.token}
                    </option>
                  ))}
                </select>
                <Input
                  size="sm"
                  placeholder="ID do canal Discord"
                  value={newChannelId}
                  onChange={(e) => setNewChannelId(e.target.value)}
                  startContent={<FontAwesomeIcon icon={faHashtag} className="text-foreground/30 text-xs" />}
                />
                <Button
                  size="sm"
                  color="primary"
                  onPress={handleAddChannel}
                  isLoading={addingChannel}
                  isDisabled={!selectedTokenId || !newChannelId.trim()}
                  startContent={<FontAwesomeIcon icon={faPlus} />}
                >
                  Adicionar Canal
                </Button>
              </div>
              <p className="text-xs text-foreground/40 flex items-center gap-1.5">
                <FontAwesomeIcon icon={faCircleInfo} className="text-[10px]" />
                A conta deve ter acesso ao canal. O slowmode é detectado automaticamente.
              </p>
            </div>

            {/* Channels por token */}
            {tokens.length === 0 ? (
              <div className="rounded-xl border border-dashed border-foreground/15 p-8 text-center">
                <p className="text-sm text-foreground/50">Adicione tokens primeiro</p>
              </div>
            ) : (
              tokens.map((token) => (
                <div key={token.id} className="space-y-2">
                  {/* Token header */}
                  <div className="flex items-center gap-2 px-1">
                    {token.avatar ? (
                      <img src={token.avatar} alt="" className="w-5 h-5 rounded-full" />
                    ) : (
                      <FontAwesomeIcon icon={faUser} className="text-foreground/30 text-xs" />
                    )}
                    <span className="text-sm font-semibold">
                      {token.label || token.username || token.token}
                    </span>
                    <span className="text-xs text-foreground/40">
                      ({token.channels.length} canal(is))
                    </span>

                    {token.channels.length > 0 && tokens.length > 1 && (
                      <button
                        onClick={() => setCopyModalSourceId(token.id)}
                        className="ml-auto flex items-center gap-1.5 text-xs text-foreground/40 hover:text-primary transition-colors"
                      >
                        <FontAwesomeIcon icon={faArrowRightArrowLeft} className="text-[10px]" />
                        Copiar canais
                      </button>
                    )}
                  </div>

                  {token.channels.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-foreground/10 p-4 text-center">
                      <p className="text-xs text-foreground/40">Nenhum canal configurado</p>
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {token.channels.map((ch) => (
                        <ChannelRow
                          key={ch.channelId}
                          ch={ch}
                          tokenId={token.id}
                          onDelete={() => handleDeleteChannel(token.id, ch.channelId)}
                          onToggle={(v) => handleToggleChannel(token.id, ch.channelId, v)}
                          onSlowmodeChange={(v) => handleSlowmodeChange(token.id, ch.channelId, v)}
                          onTest={() => handleTestChannel(token.id, ch.channelId)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </Tab>

        {/* ── Tab: Logs ─────────────────────────────────────────────────────── */}
        <Tab
          key="logs"
          title={
            <span className="flex items-center gap-2">
              <FontAwesomeIcon icon={faCircleDot} className={isRunning ? "text-success animate-pulse" : ""} />
              Logs
            </span>
          }
        >
          <div className="space-y-3 mt-3">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="light"
                onPress={loadLogs}
                isLoading={logsLoading}
                startContent={<FontAwesomeIcon icon={faRotate} />}
              >
                Atualizar logs
              </Button>
              {isRunning && (
                <Chip size="sm" color="success" variant="dot">
                  Auto-refresh ativo
                </Chip>
              )}
            </div>

            <div
              ref={logsRef}
              className="rounded-xl border border-foreground/10 bg-foreground/[0.02] divide-y divide-foreground/5 max-h-[500px] overflow-y-auto"
            >
              {logs.length === 0 ? (
                <div className="p-8 text-center">
                  <p className="text-sm text-foreground/40">Nenhum log disponível</p>
                </div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="flex items-start gap-3 px-4 py-2.5">
                    <span
                      className={`text-[10px] font-mono mt-0.5 shrink-0 ${
                        log.level === "success"
                          ? "text-success"
                          : log.level === "error"
                          ? "text-danger"
                          : log.level === "warn"
                          ? "text-warning"
                          : "text-foreground/40"
                      }`}
                    >
                      {new Date(log.ts).toLocaleTimeString("pt-BR")}
                    </span>

                    <span
                      className={`text-[10px] font-bold uppercase shrink-0 w-12 ${
                        log.level === "success"
                          ? "text-success"
                          : log.level === "error"
                          ? "text-danger"
                          : log.level === "warn"
                          ? "text-warning"
                          : "text-foreground/30"
                      }`}
                    >
                      {log.level}
                    </span>

                    {log.token && (
                      <span className="text-xs text-primary/70 shrink-0 truncate max-w-[120px]">
                        {log.token}
                      </span>
                    )}

                    {log.channel && (
                      <span className="text-xs text-foreground/40 font-mono shrink-0">
                        #{log.channel.slice(0, 8)}
                      </span>
                    )}

                    <span className="text-xs text-foreground/70 flex-1">{log.msg}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </Tab>
      </Tabs>
    </div>
  );
}