"use client";

/**
 * RequirementsSection.tsx
 * Seção da dashboard admin para gerenciar o requirements.txt global dos bots.
 * Pode ser incluída em qualquer página (ex: dentro de admin/bot ou admin/updates).
 */

import { useState, useEffect } from "react";
import {
  Package,
  Save,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Clock,
  Zap,
} from "lucide-react";

type SaveStatus = "idle" | "saving" | "saved" | "error";

export function RequirementsSection() {
  const [requirements, setRequirements] = useState("");
  const [original, setOriginal] = useState("");
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [rebuildStatus, setRebuildStatus] = useState<SaveStatus>("idle");
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [rebuildTotal, setRebuildTotal] = useState<number | null>(null);

  useEffect(() => {
    fetchRequirements();
  }, []);

  const fetchRequirements = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/bot/requirements", {
        credentials: "include",
      });
      const data = await res.json();
      if (data.success) {
        setRequirements(data.requirements);
        setOriginal(data.requirements);
        setLastSaved(data.updatedAt);
      }
    } catch (e) {
      console.error("Erro ao carregar requirements:", e);
    } finally {
      setLoading(false);
    }
  };

  const isDirty = requirements !== original;

  const save = async (rebuild: boolean) => {
    const setter = rebuild ? setRebuildStatus : setSaveStatus;
    setter("saving");
    setErrorMsg("");

    try {
      const res = await fetch("/api/admin/bot/requirements", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirements, rebuild }),
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Erro ao salvar");
      }

      setOriginal(requirements);
      setLastSaved(data.updatedAt);
      if (rebuild && data.totalBots != null) {
        setRebuildTotal(data.totalBots);
      }
      setter("saved");
      setTimeout(() => setter("idle"), 3000);
    } catch (err: any) {
      setErrorMsg(err.message || "Erro desconhecido");
      setter("error");
      setTimeout(() => setter("idle"), 4000);
    }
  };

  const lineCount = requirements.split("\n").length;
  const packageCount = requirements
    .split("\n")
    .filter((l) => l.trim() && !l.trim().startsWith("#")).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-foreground/40">
        <RefreshCw className="w-5 h-5 animate-spin mr-2" />
        Carregando requirements...
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-3 bg-primary/10 rounded-xl">
          <Package className="w-7 h-7 text-primary" />
        </div>
        <div>
          <h2 className="text-2xl font-bold">requirements.txt Global</h2>
          <p className="text-sm text-foreground/60">
            Aplicado automaticamente em todos os deploys e rebuilds
          </p>
        </div>
      </div>

      {/* Info banner */}
      <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
        <div className="text-sm">
          <p className="font-medium text-blue-500 mb-1">Como funciona</p>
          <p className="text-foreground/70">
            <strong>Salvar</strong> apenas atualiza o banco — o novo requirements.txt
            será injetado nos próximos deploys/commits automaticamente.
            <br />
            <strong>Salvar + Rebuild</strong> salva <em>e</em> faz commit do
            requirements.txt em todos os bots ativos agora, em background.
          </p>
        </div>
      </div>

      {/* Meta info */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-foreground/50">
        <span className="flex items-center gap-1">
          <Package className="w-3.5 h-3.5" />
          {packageCount} pacote(s)
        </span>
        <span className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" />
          {lastSaved
            ? `Salvo em ${new Date(lastSaved).toLocaleString("pt-BR")}`
            : "Nunca salvo"}
        </span>
        {isDirty && (
          <span className="text-yellow-500 font-medium">● Alterações não salvas</span>
        )}
      </div>

      {/* Editor */}
      <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 bg-foreground/5 border-b border-foreground/10">
          <span className="text-xs font-mono text-foreground/50">requirements.txt</span>
          <span className="text-xs text-foreground/40">{lineCount} linhas</span>
        </div>

        {/* Line numbers + textarea */}
        <div className="flex font-mono text-sm">
          {/* Line numbers */}
          <div className="select-none text-right text-foreground/25 px-3 pt-4 pb-4 bg-foreground/[0.02] border-r border-foreground/10 min-w-[3rem]">
            {requirements.split("\n").map((_, i) => (
              <div key={i} className="leading-6">
                {i + 1}
              </div>
            ))}
          </div>

          {/* Textarea */}
          <textarea
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
            spellCheck={false}
            className="flex-1 px-4 py-4 bg-transparent resize-none focus:outline-none leading-6 text-foreground/90 placeholder:text-foreground/25"
            style={{ minHeight: "320px" }}
            placeholder="# Ex: requests>=2.28.0"
          />
        </div>
      </div>

      {/* Error message */}
      {errorMsg && (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {errorMsg}
        </div>
      )}

      {/* Rebuild success banner */}
      {rebuildStatus === "saved" && rebuildTotal != null && (
        <div className="flex items-center gap-2 text-green-400 text-sm bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          Rebuild iniciado em <strong>{rebuildTotal}</strong> bot(s) em background.
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Salvar */}
        <button
          onClick={() => save(false)}
          disabled={!isDirty || saveStatus === "saving" || rebuildStatus === "saving"}
          className="flex-1 flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold transition-all
            disabled:opacity-40 disabled:cursor-not-allowed
            bg-foreground/10 hover:bg-foreground/15 text-foreground border border-foreground/15"
        >
          {saveStatus === "saving" ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : saveStatus === "saved" ? (
            <CheckCircle className="w-4 h-4 text-green-500" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {saveStatus === "saving"
            ? "Salvando..."
            : saveStatus === "saved"
            ? "Salvo!"
            : "Salvar"}
        </button>

        {/* Salvar + Rebuild */}
        <button
          onClick={() => save(true)}
          disabled={!isDirty || saveStatus === "saving" || rebuildStatus === "saving"}
          className="flex-1 flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold transition-all
            disabled:opacity-40 disabled:cursor-not-allowed
            bg-primary hover:bg-primary/90 text-white shadow-lg shadow-primary/20"
        >
          {rebuildStatus === "saving" ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : rebuildStatus === "saved" ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <Zap className="w-4 h-4" />
          )}
          {rebuildStatus === "saving"
            ? "Iniciando rebuild..."
            : rebuildStatus === "saved"
            ? "Rebuild iniciado!"
            : "Salvar + Rebuild"}
        </button>
      </div>

      <p className="text-xs text-foreground/35 text-center">
        O rebuild não reinicia os bots — apenas atualiza o arquivo. A Stackr aplicará na próxima inicialização.
      </p>
    </div>
  );
}