"use client";

/**
 * src/app/dashboard/admin/sections/discord/DiscordConfigSection.tsx
 *
 * Seção de configuração Discord no painel admin.
 * Permite configurar token, guild, canais de contador, feedbacks e vendas
 * sem precisar mexer em variáveis de ambiente.
 */

import { useState, useEffect, useCallback } from "react";
import {
  Bot,
  Save,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
  EyeOff,
  Wifi,
  WifiOff,
  Hash,
  Mic,
  MessageSquare,
  ShoppingBag,
  Users,
  Shield,
  Info,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ConfigField {
  key: string;
  value: string;
  updatedAt: string | null;
  updatedBy: string | null;
  fromEnv: boolean;
}

interface Config {
  discord_guild_id: ConfigField;
  discord_bot_token: ConfigField;
  discord_counter_channel_id: ConfigField;
  discord_feedback_channel_id: ConfigField;
  discord_sales_channel_id: ConfigField;
  discord_default_role_id: ConfigField;
}

interface TestResult {
  success: boolean;
  error?: string;
  bot?: { id: string; username: string; avatar: string | null };
  guild?: { id: string; name: string; memberCount: number } | null;
}

type SaveStatus = "idle" | "saving" | "saved" | "error";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(d?: string | null) {
  if (!d) return null;
  return new Date(d).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ─── Config Item ──────────────────────────────────────────────────────────────

interface ConfigItemProps {
  label: string;
  description: string;
  icon: React.ReactNode;
  fieldKey: string;
  value: string;
  onChange: (key: string, val: string) => void;
  sensitive?: boolean;
  placeholder?: string;
  updatedAt?: string | null;
  fromEnv?: boolean;
  badge?: React.ReactNode;
}

function ConfigItem({
  label,
  description,
  icon,
  fieldKey,
  value,
  onChange,
  sensitive = false,
  placeholder = "",
  updatedAt,
  fromEnv,
  badge,
}: ConfigItemProps) {
  const [reveal, setReveal] = useState(false);

  return (
    <div className="group flex flex-col gap-2 p-4 rounded-xl border border-foreground/8 bg-foreground/[0.02] hover:border-foreground/15 transition-all">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-foreground/8 text-foreground/50 flex-shrink-0">
            {icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold">{label}</p>
              {badge}
              {fromEnv && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 font-medium">
                  via .env
                </span>
              )}
            </div>
            <p className="text-xs text-foreground/40 mt-0.5">{description}</p>
          </div>
        </div>
        {updatedAt && (
          <p className="text-[10px] text-foreground/30 flex-shrink-0 mt-1">
            {fmtDate(updatedAt)}
          </p>
        )}
      </div>

      {/* Input */}
      <div className="relative">
        <input
          type={sensitive && !reveal ? "password" : "text"}
          value={value}
          onChange={(e) => onChange(fieldKey, e.target.value)}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          className="w-full px-3 py-2.5 bg-background/60 border border-foreground/10 rounded-lg text-sm font-mono focus:outline-none focus:ring-1 focus:ring-primary/60 focus:border-primary/40 transition-all placeholder:text-foreground/20 pr-10"
        />
        {sensitive && (
          <button
            type="button"
            onClick={() => setReveal((v) => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/30 hover:text-foreground/70 transition-colors"
          >
            {reveal ? (
              <EyeOff className="w-3.5 h-3.5" />
            ) : (
              <Eye className="w-3.5 h-3.5" />
            )}
          </button>
        )}
      </div>

      {/* Key hint */}
      <p className="text-[10px] text-foreground/20 font-mono">{fieldKey}</p>
    </div>
  );
}

// ─── Test Card ────────────────────────────────────────────────────────────────

function TestCard({
  result,
  loading,
  onTest,
}: {
  result: TestResult | null;
  loading: boolean;
  onTest: () => void;
}) {
  return (
    <div
      className={`rounded-xl border p-5 transition-all ${
        result === null
          ? "border-foreground/10 bg-foreground/[0.02]"
          : result.success
          ? "border-green-500/20 bg-green-500/[0.03]"
          : "border-red-500/20 bg-red-500/[0.03]"
      }`}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div
            className={`p-2 rounded-lg ${
              result?.success
                ? "bg-green-500/10 text-green-400"
                : "bg-foreground/8 text-foreground/40"
            }`}
          >
            {result?.success ? (
              <Wifi className="w-4 h-4" />
            ) : (
              <WifiOff className="w-4 h-4" />
            )}
          </div>
          <div>
            <p className="text-sm font-semibold">Testar Conexão</p>
            <p className="text-xs text-foreground/40">
              Valida token e verifica acesso ao servidor
            </p>
          </div>
        </div>
        <button
          onClick={onTest}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-foreground/15 text-sm font-medium hover:bg-foreground/8 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {loading ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Wifi className="w-3.5 h-3.5" />
          )}
          {loading ? "Testando..." : "Testar"}
        </button>
      </div>

      {result && (
        <>
          {result.success ? (
            <div className="space-y-3">
              {/* Bot info */}
              <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/10">
                {result.bot?.avatar ? (
                  <img
                    src={result.bot.avatar}
                    alt=""
                    className="w-10 h-10 rounded-full"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-foreground/10 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-foreground/40" />
                  </div>
                )}
                <div>
                  <p className="text-sm font-semibold text-green-400">
                    ✓ Bot conectado
                  </p>
                  <p className="text-xs text-foreground/60">
                    @{result.bot?.username} ({result.bot?.id})
                  </p>
                </div>
              </div>

              {/* Guild info */}
              {result.guild ? (
                <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/10">
                  <Users className="w-5 h-5 text-green-400 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-green-400">
                      ✓ Servidor encontrado
                    </p>
                    <p className="text-xs text-foreground/60">
                      {result.guild.name} —{" "}
                      {result.guild.memberCount?.toLocaleString()} membros
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-3 p-3 rounded-lg bg-yellow-500/5 border border-yellow-500/10">
                  <AlertCircle className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                  <p className="text-xs text-yellow-400">
                    Guild ID não configurado ou bot não está no servidor
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2.5 p-3 rounded-lg bg-red-500/5 border border-red-500/10">
              <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <p className="text-sm text-red-400">{result.error}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Main Section ──────────────────────────────────────────────────────────────

export function DiscordConfigSection() {
  const [config, setConfig] = useState<Partial<Config>>({});
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testLoading, setTestLoading] = useState(false);

  // ── Load ────────────────────────────────────────────────────────────────────

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/discord-config", {
        credentials: "include",
      });
      const data = await res.json();
      if (data.success) {
        setConfig(data.config);
        // Inicializa draft com os valores mascarados (não editáveis = "")
        const initial: Record<string, string> = {};
        for (const [key, field] of Object.entries(
          data.config as Config
        )) {
          // Campos sensíveis mascarados no servidor — deixa o draft vazio
          // para que o usuário precise digitar o novo valor explicitamente
          const isMasked =
            typeof field.value === "string" && field.value.includes("...");
          initial[key] = isMasked ? "" : field.value;
        }
        setDraft(initial);
      }
    } catch (e) {
      console.error("Erro ao carregar config Discord:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // ── Save ────────────────────────────────────────────────────────────────────

  const handleSave = async () => {
    setSaveStatus("saving");
    setErrorMsg("");

    // Só envia campos que foram modificados (não-vazios) ou explicitamente limpos
    const payload: Record<string, string> = {};
    for (const [key, value] of Object.entries(draft)) {
      const original = (config as any)[key]?.value ?? "";
      // Inclui se: campo preenchido OU campo foi limpo (era non-empty, agora vazio)
      if (value !== "" || (original !== "" && !original.includes("..."))) {
        payload[key] = value;
      }
    }

    if (Object.keys(payload).length === 0) {
      setSaveStatus("idle");
      return;
    }

    try {
      const res = await fetch("/api/admin/discord-config", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Erro ao salvar");
      }

      setSaveStatus("saved");
      setTestResult(null); // limpa resultado do teste após salvar
      setTimeout(() => setSaveStatus("idle"), 3000);
      await load(); // recarrega valores do servidor
    } catch (err: any) {
      setErrorMsg(err.message || "Erro desconhecido");
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 4000);
    }
  };

  // ── Test ────────────────────────────────────────────────────────────────────

  const handleTest = async () => {
    setTestLoading(true);
    setTestResult(null);
    try {
      const res = await fetch("/api/admin/discord-config/test", {
        method: "POST",
        credentials: "include",
      });
      const data = await res.json();
      setTestResult(data);
    } catch {
      setTestResult({ success: false, error: "Erro de conexão" });
    } finally {
      setTestLoading(false);
    }
  };

  // ── onChange ─────────────────────────────────────────────────────────────────

  const handleChange = (key: string, value: string) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
    if (saveStatus !== "idle") setSaveStatus("idle");
  };

  // ── Render ────────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-foreground/40">
        <RefreshCw className="w-5 h-5 animate-spin mr-2" />
        Carregando configurações...
      </div>
    );
  }

  const fields = config as Config;
  const isDirty = Object.entries(draft).some(
    ([key, val]) => val !== "" || (fields[key as keyof Config]?.value ?? "").includes("...")
      ? false
      : val !== (fields[key as keyof Config]?.value ?? "")
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="p-3 bg-[#5865F2]/10 rounded-xl">
          <Bot className="w-7 h-7 text-[#5865F2]" />
        </div>
        <div className="flex-1">
          <h2 className="text-2xl font-bold">Configurações Discord</h2>
          <p className="text-sm text-foreground/50">
            Gerencie token, servidor e canais sem precisar alterar variáveis de
            ambiente
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saveStatus === "saving"}
          className="flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-primary/20"
        >
          {saveStatus === "saving" ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : saveStatus === "saved" ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {saveStatus === "saving"
            ? "Salvando..."
            : saveStatus === "saved"
            ? "Salvo!"
            : "Salvar Configurações"}
        </button>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-[#5865F2]/8 border border-[#5865F2]/20">
        <Info className="w-4 h-4 text-[#7289da] flex-shrink-0 mt-0.5" />
        <div className="text-xs text-foreground/70 space-y-1">
          <p>
            <strong className="text-foreground/90">Prioridade:</strong> valores
            salvos aqui sobrescrevem as variáveis de ambiente. Se um campo
            estiver vazio, o sistema usa o <code className="bg-foreground/8 px-1 rounded">.env</code> como
            fallback.
          </p>
          <p>
            Para <strong>limpar</strong> um valor e voltar ao .env, salve o
            campo vazio.
          </p>
        </div>
      </div>

      {/* Error */}
      {saveStatus === "error" && errorMsg && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          {errorMsg}
        </div>
      )}

      {/* ── Seção: Geral ──────────────────────────────────────────────────────── */}
      <section className="space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <Shield className="w-4 h-4 text-foreground/40" />
          <h3 className="text-sm font-semibold text-foreground/70 uppercase tracking-wider">
            Autenticação &amp; Servidor
          </h3>
        </div>

        <ConfigItem
          fieldKey="discord_bot_token"
          label="Token do Bot"
          description="Token de autenticação do bot Discord. Mantido criptografado no banco."
          icon={<Bot className="w-4 h-4" />}
          value={draft["discord_bot_token"] ?? ""}
          onChange={handleChange}
          sensitive
          placeholder="Bot.XXXXXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
          updatedAt={fields.discord_bot_token?.updatedAt}
          fromEnv={fields.discord_bot_token?.fromEnv}
        />

        <ConfigItem
          fieldKey="discord_guild_id"
          label="Guild ID (Servidor Principal)"
          description="ID numérico do servidor Discord principal da plataforma."
          icon={<Users className="w-4 h-4" />}
          value={draft["discord_guild_id"] ?? ""}
          onChange={handleChange}
          placeholder="Ex: 1234567890123456789"
          updatedAt={fields.discord_guild_id?.updatedAt}
          fromEnv={fields.discord_guild_id?.fromEnv}
        />

        <ConfigItem
          fieldKey="discord_default_role_id"
          label="Cargo Padrão (Cliente)"
          description="ID do cargo atribuído automaticamente ao usuário após a primeira compra ou plano gratuito."
          icon={<Shield className="w-4 h-4" />}
          value={draft["discord_default_role_id"] ?? ""}
          onChange={handleChange}
          placeholder="Ex: 9876543210987654321"
          updatedAt={fields.discord_default_role_id?.updatedAt}
          fromEnv={fields.discord_default_role_id?.fromEnv}
        />
      </section>

      {/* ── Seção: Canais ─────────────────────────────────────────────────────── */}
      <section className="space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <Hash className="w-4 h-4 text-foreground/40" />
          <h3 className="text-sm font-semibold text-foreground/70 uppercase tracking-wider">
            Canais
          </h3>
        </div>

        <ConfigItem
          fieldKey="discord_counter_channel_id"
          label="Canal Contador de Aplicações"
          description="Canal de voz cujo nome é atualizado automaticamente com o total de aplicações."
          icon={<Mic className="w-4 h-4" />}
          value={draft["discord_counter_channel_id"] ?? ""}
          onChange={handleChange}
          placeholder="ID do canal de voz"
          updatedAt={fields.discord_counter_channel_id?.updatedAt}
          fromEnv={fields.discord_counter_channel_id?.fromEnv}
          badge={
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-medium">
              Canal de voz
            </span>
          }
        />

        <ConfigItem
          fieldKey="discord_feedback_channel_id"
          label="Canal de Feedbacks"
          description="Canal de texto de onde os feedbacks são lidos para exibição no site."
          icon={<MessageSquare className="w-4 h-4" />}
          value={draft["discord_feedback_channel_id"] ?? ""}
          onChange={handleChange}
          placeholder="ID do canal de texto"
          updatedAt={fields.discord_feedback_channel_id?.updatedAt}
          fromEnv={fields.discord_feedback_channel_id?.fromEnv}
          badge={
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
              Canal de texto
            </span>
          }
        />

        <ConfigItem
          fieldKey="discord_sales_channel_id"
          label="Canal de Logs de Vendas"
          description="Canal onde são enviadas notificações automáticas quando uma compra é aprovada via PIX."
          icon={<ShoppingBag className="w-4 h-4" />}
          value={draft["discord_sales_channel_id"] ?? ""}
          onChange={handleChange}
          placeholder="ID do canal de texto"
          updatedAt={fields.discord_sales_channel_id?.updatedAt}
          fromEnv={fields.discord_sales_channel_id?.fromEnv}
          badge={
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20 font-medium">
              Novo
            </span>
          }
        />
      </section>

      {/* ── Teste de conexão ──────────────────────────────────────────────────── */}
      <TestCard
        result={testResult}
        loading={testLoading}
        onTest={handleTest}
      />

      {/* ── Referência de IDs esperados ───────────────────────────────────────── */}
      <div className="rounded-xl border border-foreground/8 bg-foreground/[0.02] overflow-hidden">
        <div className="px-5 py-3 border-b border-foreground/8 flex items-center gap-2">
          <Info className="w-3.5 h-3.5 text-foreground/30" />
          <p className="text-xs font-semibold text-foreground/40 uppercase tracking-wider">
            Como encontrar IDs no Discord
          </p>
        </div>
        <div className="px-5 py-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-foreground/50">
          <div>
            <p className="font-semibold text-foreground/70 mb-1">
              Guild / Canal / Cargo ID
            </p>
            <ol className="space-y-1 list-decimal list-inside">
              <li>Habilite Modo Desenvolvedor no Discord</li>
              <li>
                Clique com o botão direito no servidor, canal ou cargo
              </li>
              <li>Selecione "Copiar ID"</li>
            </ol>
          </div>
          <div>
            <p className="font-semibold text-foreground/70 mb-1">
              Tipo de canal esperado
            </p>
            <ul className="space-y-1">
              <li>
                <span className="text-purple-400 font-mono">contador</span> →
                Canal de voz (Voice)
              </li>
              <li>
                <span className="text-blue-400 font-mono">feedbacks</span> →
                Canal de texto ou fórum
              </li>
              <li>
                <span className="text-green-400 font-mono">vendas</span> →
                Canal de texto privado
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}