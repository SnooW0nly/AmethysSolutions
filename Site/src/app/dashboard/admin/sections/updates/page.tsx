"use client";

/**
 * src/app/dashboard/admin/sections/updates/page.tsx
 *
 * Sub-navigation: Mass Updates | Changelogs
 */

import { useState, useEffect, useRef } from "react";
import {
  Upload,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Zap,
  Folder,
  FolderOpen,
  Trash2,
  ChevronRight,
  X,
  FileText,
  GitCommit,
  Search,
} from "lucide-react";
import { ChangelogsSection } from "../changelogs/ChangelogsSection";

// ─────────────────────────────────────────────────────────────────────────────
// MASS UPDATE CONTENT (original code, unchanged)
// ─────────────────────────────────────────────────────────────────────────────

function MassUpdateContent() {
  const [plans, setPlans] = useState<any[]>([]);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [updateVersion, setUpdateVersion] = useState("");
  const [uploading, setUploading] = useState(false);

  const [step, setStep] = useState<"form" | "folders" | "running">("form");
  const [loadingFolders, setLoadingFolders] = useState(false);
  const [availableFolders, setAvailableFolders] = useState<string[]>([]);
  const [selectedFolders, setSelectedFolders] = useState<Set<string>>(
    new Set()
  );
  const [uploadedZipPath, setUploadedZipPath] = useState<string | null>(null);

  const [currentUpdate, setCurrentUpdate] = useState<any>(null);
  const [updateHistory, setUpdateHistory] = useState<any[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadPlans();
    loadHistory();
  }, []);

  useEffect(() => {
    if (autoScroll && logsEndRef.current && currentUpdate?.logs) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [currentUpdate?.logs?.length, autoScroll]);

  useEffect(() => {
    if (currentUpdate?.id && currentUpdate?.status === "running") {
      const interval = setInterval(() => {
        fetchProgress(currentUpdate.id);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [currentUpdate?.id, currentUpdate?.status]);

  const loadPlans = async () => {
    try {
      const res = await fetch("/api/admin/plans/list", {
        credentials: "include",
      });
      const data = await res.json();
      if (data.success) setPlans(data.data);
    } catch (e) {
      console.error("Erro ao carregar planos:", e);
    }
  };

  const loadHistory = async () => {
    try {
      const res = await fetch("/api/admin/updates/list", {
        credentials: "include",
      });
      const data = await res.json();
      if (data.success) setUpdateHistory(data.data);
    } catch (e) {
      console.error("Erro ao carregar histórico:", e);
    }
  };

  const fetchProgress = async (updateId: string) => {
    try {
      const res = await fetch(
        `/api/admin/updates/progress/${updateId}`,
        { credentials: "include" }
      );
      const data = await res.json();
      if (data.success) {
        setCurrentUpdate(data.data);
        if (data.data.status !== "running") loadHistory();
      }
    } catch (e) {
      console.error("Erro ao buscar progresso:", e);
    }
  };

  const handleHistoryClick = async (update: any) => {
    if (update.updateId && !update.logs) {
      await fetchProgress(update.updateId);
    } else {
      setCurrentUpdate(update);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0]);
      setAvailableFolders([]);
      setSelectedFolders(new Set());
      setUploadedZipPath(null);
      setStep("form");
    }
  };

  const handleAnalyzeFolders = async () => {
    if (!selectedPlan || !file) {
      alert("Selecione um plano e um arquivo ZIP");
      return;
    }
    setLoadingFolders(true);
    try {
      const formData = new FormData();
      formData.append("planId", selectedPlan);
      formData.append("file", file);
      if (updateVersion.trim()) formData.append("updateVersion", updateVersion.trim());
      const res = await fetch("/api/admin/updates/analyze", {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      const data = await res.json();
      if (!data.success) {
        alert(data.message || "Erro ao analisar ZIP");
        return;
      }
      setUploadedZipPath(data.data.zipPath);
      setAvailableFolders(data.data.folders);
      setSelectedFolders(new Set());
      setStep("folders");
    } catch (e) {
      console.error("Erro ao analisar ZIP:", e);
      alert("Erro ao analisar ZIP");
    } finally {
      setLoadingFolders(false);
    }
  };

  const toggleFolder = (folder: string) => {
    setSelectedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folder)) next.delete(folder);
      else next.add(folder);
      return next;
    });
  };

  const handleStartUpdate = async () => {
    if (!uploadedZipPath) return;
    setUploading(true);
    try {
      const body: any = {
        planId: selectedPlan,
        zipPath: uploadedZipPath,
        foldersToDelete: JSON.stringify(Array.from(selectedFolders)),
      };
      if (updateVersion.trim()) body.updateVersion = updateVersion.trim();
      const res = await fetch("/api/admin/updates/start-from-path", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.success) {
        fetchProgress(data.data.updateId);
        setFile(null);
        setAvailableFolders([]);
        setSelectedFolders(new Set());
        setUploadedZipPath(null);
        setStep("running");
        if (fileInputRef.current) fileInputRef.current.value = "";
      } else {
        alert(data.message || "Erro ao iniciar atualização");
      }
    } catch (e) {
      console.error("Erro ao iniciar atualização:", e);
      alert("Erro ao iniciar atualização");
    } finally {
      setUploading(false);
    }
  };

  const handleBackToForm = () => {
    setStep("form");
    setAvailableFolders([]);
    setSelectedFolders(new Set());
    setUploadedZipPath(null);
  };

  const getLogIcon = (type: string) => {
    switch (type) {
      case "success":
        return <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />;
      case "error":
        return <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />;
      case "warning":
        return <AlertCircle className="w-4 h-4 text-yellow-500 flex-shrink-0" />;
      default:
        return <Clock className="w-4 h-4 text-blue-500 flex-shrink-0" />;
    }
  };

  const getLogColor = (type: string) => {
    switch (type) {
      case "success":
        return "text-green-400";
      case "error":
        return "text-red-400";
      case "warning":
        return "text-yellow-400";
      default:
        return "text-foreground/70";
    }
  };

  const progressPercentage =
    currentUpdate && currentUpdate.total > 0
      ? Math.round(
          ((currentUpdate.processed || 0) / currentUpdate.total) * 100
        )
      : 0;

  const isRunning = currentUpdate?.status === "running";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-3 bg-primary/10 rounded-xl">
          <Zap className="w-7 h-7 text-primary" />
        </div>
        <div>
          <h1 className="text-3xl font-bold">Atualização em Massa</h1>
          <p className="text-sm text-foreground/60">
            Atualize todos os bots de um plano de uma vez
          </p>
        </div>
      </div>

      <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-500 mb-1">
              Rastreamento de Atualizações
            </p>
            <p className="text-xs text-foreground/70">
              O sistema registra automaticamente a data e hora de cada
              atualização no banco de dados, permitindo saber exatamente quando
              cada bot foi atualizado pela última vez.
            </p>
          </div>
        </div>
      </div>

      {step === "form" && (
        <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl p-6">
          <h2 className="text-xl font-bold mb-4">Iniciar Nova Atualização</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="text-sm text-foreground/70 mb-2 block font-medium">
                Plano
              </label>
              <select
                value={selectedPlan}
                onChange={(e) => setSelectedPlan(e.target.value)}
                disabled={isRunning}
                className="w-full px-4 py-2.5 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all disabled:opacity-50"
              >
                <option value="">Selecione um plano</option>
                {plans.map((plan) => (
                  <option key={plan.id} value={plan.id}>
                    {plan.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-foreground/70 mb-2 block font-medium">
                Código de Versão (Opcional)
              </label>
              <input
                type="text"
                value={updateVersion}
                onChange={(e) => setUpdateVersion(e.target.value)}
                placeholder="Ex: v2.5.0 ou deixe vazio"
                disabled={isRunning}
                className="w-full px-4 py-2.5 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all disabled:opacity-50 placeholder:text-foreground/30"
              />
            </div>
            <div>
              <label className="text-sm text-foreground/70 mb-2 block font-medium">
                Arquivo ZIP
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                onChange={handleFileSelect}
                disabled={isRunning}
                className="w-full px-4 py-2.5 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all disabled:opacity-50 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-white hover:file:bg-primary/90"
              />
            </div>
          </div>
          {file && (
            <div className="mb-4 p-3 bg-foreground/5 rounded-lg">
              <p className="text-sm text-foreground/70">
                <strong>Arquivo selecionado:</strong> {file.name} (
                {(file.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            </div>
          )}
          <button
            onClick={handleAnalyzeFolders}
            disabled={!selectedPlan || !file || loadingFolders || isRunning}
            className="w-full px-4 py-3 bg-primary hover:bg-primary/90 disabled:bg-foreground/10 disabled:text-foreground/30 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all flex items-center justify-center gap-2"
          >
            {loadingFolders ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                Analisando ZIP...
              </>
            ) : (
              <>
                <ChevronRight className="w-5 h-5" />
                Próximo: Selecionar Pastas
              </>
            )}
          </button>
        </div>
      )}

      {step === "folders" && (
        <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl p-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xl font-bold">Selecionar Pastas para Apagar</h2>
            <button
              onClick={handleBackToForm}
              className="flex items-center gap-1 text-sm text-foreground/50 hover:text-foreground/80 transition-colors"
            >
              <X className="w-4 h-4" /> Voltar
            </button>
          </div>
          <p className="text-sm text-foreground/60 mb-5">
            Selecione as pastas que serão{" "}
            <strong>apagadas de cada bot</strong> antes do commit.
          </p>
          {availableFolders.length === 0 ? (
            <div className="text-center py-10 text-foreground/40">
              <Folder className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-sm">Nenhuma pasta encontrada no ZIP</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
              {availableFolders.map((folder) => {
                const selected = selectedFolders.has(folder);
                return (
                  <button
                    key={folder}
                    onClick={() => toggleFolder(folder)}
                    className={`flex items-center gap-2.5 px-4 py-3 rounded-xl border text-left transition-all ${
                      selected
                        ? "bg-red-500/10 border-red-500/40 text-red-400"
                        : "bg-foreground/5 border-foreground/10 text-foreground/70 hover:bg-foreground/10 hover:border-foreground/20"
                    }`}
                  >
                    {selected ? (
                      <FolderOpen className="w-4 h-4 flex-shrink-0" />
                    ) : (
                      <Folder className="w-4 h-4 flex-shrink-0" />
                    )}
                    <span className="text-sm font-mono truncate">{folder}</span>
                    {selected && (
                      <Trash2 className="w-3.5 h-3.5 ml-auto flex-shrink-0 opacity-70" />
                    )}
                  </button>
                );
              })}
            </div>
          )}
          <div className="flex flex-wrap items-center gap-3 mb-5">
            {selectedFolders.size > 0 ? (
              <div className="flex flex-wrap gap-2">
                {Array.from(selectedFolders).map((f) => (
                  <span
                    key={f}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-red-500/10 text-red-400 text-xs font-mono rounded-lg border border-red-500/20"
                  >
                    <Trash2 className="w-3 h-3" />
                    {f}
                    <button
                      onClick={() => toggleFolder(f)}
                      className="ml-0.5 hover:text-red-300"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-sm text-foreground/40 italic">
                Nenhuma pasta selecionada — apenas o commit será realizado
              </span>
            )}
          </div>
          <button
            onClick={handleStartUpdate}
            disabled={uploading}
            className="w-full px-4 py-3 bg-primary hover:bg-primary/90 disabled:bg-foreground/10 disabled:text-foreground/30 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all flex items-center justify-center gap-2"
          >
            {uploading ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                Iniciando...
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                {selectedFolders.size > 0
                  ? `Apagar ${selectedFolders.size} pasta(s) e enviar atualização`
                  : "Enviar atualização"}
              </>
            )}
          </button>
        </div>
      )}

      {currentUpdate && (
        <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">Atualização em Andamento</h2>
            <div className="flex items-center gap-2">
              {isRunning && (
                <RefreshCw className="w-5 h-5 text-primary animate-spin" />
              )}
              <span
                className={`px-3 py-1 rounded-lg text-sm font-medium ${
                  currentUpdate.status === "running"
                    ? "bg-blue-500/10 text-blue-500"
                    : currentUpdate.status === "completed"
                    ? "bg-green-500/10 text-green-500"
                    : "bg-red-500/10 text-red-500"
                }`}
              >
                {currentUpdate.status === "running"
                  ? "Em andamento"
                  : currentUpdate.status === "completed"
                  ? "Concluído"
                  : "Erro"}
              </span>
            </div>
          </div>

          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-foreground/70">
                {currentUpdate.processed || 0} / {currentUpdate.total || 0} bots
                processados
              </span>
              <span className="text-sm font-medium">{progressPercentage}%</span>
            </div>
            <div className="w-full h-3 bg-foreground/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4 mb-4">
            {[
              {
                label: "Sucesso",
                val: currentUpdate.successful || 0,
                c: "green",
              },
              { label: "Falhas", val: currentUpdate.failed || 0, c: "red" },
              { label: "Pulados", val: currentUpdate.skipped || 0, c: "yellow" },
              {
                label: "Pendentes",
                val: (currentUpdate.total || 0) - (currentUpdate.processed || 0),
                c: "blue",
              },
            ].map(({ label, val, c }) => (
              <div key={label} className={`p-3 bg-${c}-500/10 rounded-lg`}>
                <p className={`text-xs text-${c}-500 mb-1`}>{label}</p>
                <p className={`text-2xl font-bold text-${c}-500`}>{val}</p>
              </div>
            ))}
          </div>

          <div className="bg-black/50 rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm">
            {currentUpdate.logs?.length > 0 ? (
              currentUpdate.logs.map((log: any, index: number) => (
                <div
                  key={`${log.timestamp}-${index}`}
                  className="flex items-start gap-2 mb-2"
                >
                  {getLogIcon(log.type)}
                  <span className="text-foreground/50 text-xs shrink-0">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={getLogColor(log.type)}>{log.message}</span>
                </div>
              ))
            ) : (
              <div className="text-foreground/50 text-center py-8">
                Aguardando logs...
              </div>
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}

      {updateHistory.length > 0 && (
        <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl p-6">
          <h2 className="text-xl font-bold mb-4">Histórico de Atualizações</h2>
          <div className="space-y-3">
            {updateHistory.map((update) => (
              <div
                key={update.updateId || update._id || update.id}
                className="p-4 bg-foreground/5 rounded-lg hover:bg-foreground/10 transition-all cursor-pointer"
                onClick={() => handleHistoryClick(update)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Plano: {update.planId}</p>
                    <p className="text-sm text-foreground/60">
                      {new Date(update.startedAt).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-foreground/70">
                      {update.stats?.successful || update.successful || 0} /{" "}
                      {update.stats?.total || update.total || 0} sucesso
                    </p>
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        update.status === "completed"
                          ? "bg-green-500/10 text-green-500"
                          : update.status === "running"
                          ? "bg-blue-500/10 text-blue-500"
                          : "bg-red-500/10 text-red-500"
                      }`}
                    >
                      {update.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SINGLE COMMIT CONTENT
// ─────────────────────────────────────────────────────────────────────────────

function SingleCommitContent() {
  // Apps
  const [apps, setApps] = useState<any[]>([]);
  const [appsLoading, setAppsLoading] = useState(true);
  const [appSearch, setAppSearch] = useState("");
  const [selectedApp, setSelectedApp] = useState<any>(null);

  // ZIP + pastas
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<"form" | "folders">("form");
  const [analyzingFolders, setAnalyzingFolders] = useState(false);
  const [availableFolders, setAvailableFolders] = useState<string[]>([]);
  const [selectedFolders, setSelectedFolders] = useState<Set<string>>(new Set());
  const [uploadedZipPath, setUploadedZipPath] = useState<string | null>(null);

  // Submit
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Carrega todas as apps com hosting.appId
  useEffect(() => {
    const load = async () => {
      setAppsLoading(true);
      try {
        const all: any[] = [];
        let page = 1;
        while (true) {
          const res = await fetch(`/api/admin/applications?page=${page}&limit=100&sortBy=name&sortOrder=asc`, { credentials: "include" });
          if (!res.ok) break;
          const data = await res.json();
          const batch = (data.applications || []).filter((a: any) => a.hosting?.appId);
          all.push(...batch);
          if (all.length >= (data.pagination?.total || 0) || batch.length < 100) break;
          page++;
        }
        setApps(all);
      } catch (e) {
        console.error("Erro ao carregar apps:", e);
      } finally {
        setAppsLoading(false);
      }
    };
    load();
  }, []);

  const filteredApps = apps.filter((a) =>
    !appSearch ||
    a.name?.toLowerCase().includes(appSearch.toLowerCase()) ||
    a.hosting?.appId?.toLowerCase().includes(appSearch.toLowerCase())
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
    // Reseta pastas ao trocar o zip
    setAvailableFolders([]);
    setSelectedFolders(new Set());
    setUploadedZipPath(null);
    setStep("form");
  };

  const handleAnalyzeFolders = async () => {
    if (!selectedApp || !file) return;
    setAnalyzingFolders(true);
    try {
      const formData = new FormData();
      formData.append("planId", selectedApp.plan?.id || "single");
      formData.append("file", file);
      const res = await fetch("/api/admin/updates/analyze", {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      const data = await res.json();
      if (!data.success) { alert(data.message || "Erro ao analisar ZIP"); return; }
      setUploadedZipPath(data.data.zipPath);
      setAvailableFolders(data.data.folders);
      setSelectedFolders(new Set());
      setStep("folders");
    } catch (e) {
      alert("Erro ao analisar ZIP");
    } finally {
      setAnalyzingFolders(false);
    }
  };

  const toggleFolder = (folder: string) => {
    setSelectedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folder)) next.delete(folder); else next.add(folder);
      return next;
    });
  };

  const handleSubmit = async () => {
    if (!selectedApp || !file) return;
    setLoading(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("appId", selectedApp.hosting.appId);
      formData.append("file", file);
      if (selectedFolders.size > 0)
        formData.append("foldersToDelete", JSON.stringify(Array.from(selectedFolders)));
      const res = await fetch("/api/admin/updates/commit-single", {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      const data = await res.json();
      setResult(data);
      if (data.success) {
        setSelectedApp(null);
        setFile(null);
        setAvailableFolders([]);
        setSelectedFolders(new Set());
        setUploadedZipPath(null);
        setStep("form");
        setAppSearch("");
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    } catch (e: any) {
      setResult({ success: false, message: e.message || "Erro de conexão" });
    } finally {
      setLoading(false);
    }
  };

  const canAnalyze = !!selectedApp && !!file && step === "form";
  const canSubmit = !!selectedApp && !!file && !loading;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-3 bg-primary/10 rounded-xl">
          <GitCommit className="w-7 h-7 text-primary" />
        </div>
        <div>
          <h1 className="text-3xl font-bold">Commit Único</h1>
          <p className="text-sm text-foreground/60">Faça commit em um bot específico</p>
        </div>
      </div>

      <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl p-6 space-y-5">
        <h2 className="text-xl font-bold">Configurar Commit</h2>

        {/* Seleção de app */}
        <div>
          <label className="text-sm text-foreground/70 mb-2 block font-medium">Aplicação</label>
          {selectedApp ? (
            <div className="flex items-center justify-between px-4 py-3 bg-primary/5 border border-primary/20 rounded-xl">
              <div>
                <p className="font-medium text-sm">{selectedApp.name}</p>
                <p className="text-xs text-foreground/50 font-mono">{selectedApp.hosting.appId}</p>
              </div>
              <button
                onClick={() => { setSelectedApp(null); setAppSearch(""); }}
                className="text-foreground/40 hover:text-foreground/80 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-foreground/30" />
                <input
                  type="text"
                  value={appSearch}
                  onChange={(e) => setAppSearch(e.target.value)}
                  placeholder="Buscar por nome ou App ID..."
                  className="w-full pl-9 pr-4 py-2.5 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-foreground/30 text-sm"
                />
              </div>
              <div className="max-h-52 overflow-y-auto border border-foreground/10 rounded-xl divide-y divide-foreground/5 bg-background/30">
                {appsLoading ? (
                  <div className="flex items-center justify-center gap-2 py-6 text-foreground/40 text-sm">
                    <RefreshCw className="w-4 h-4 animate-spin" /> Carregando apps...
                  </div>
                ) : filteredApps.length === 0 ? (
                  <div className="py-6 text-center text-sm text-foreground/40">Nenhuma app encontrada</div>
                ) : (
                  filteredApps.map((app) => (
                    <button
                      key={app._id}
                      onClick={() => setSelectedApp(app)}
                      className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-foreground/5 transition-colors text-left"
                    >
                      <div>
                        <p className="text-sm font-medium">{app.name}</p>
                        <p className="text-xs text-foreground/40 font-mono">{app.hosting.appId}</p>
                      </div>
                      {app.plan?.name && (
                        <span className="text-[10px] px-2 py-0.5 bg-foreground/8 rounded-lg text-foreground/50">
                          {app.plan.name}
                        </span>
                      )}
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* ZIP */}
        <div>
          <label className="text-sm text-foreground/70 mb-2 block font-medium">Arquivo ZIP</label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            onChange={handleFileChange}
            className="w-full px-4 py-2.5 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-white hover:file:bg-primary/90"
          />
        </div>

        {/* Botão analisar pastas */}
        {step === "form" && (
          <button
            onClick={handleAnalyzeFolders}
            disabled={!canAnalyze || analyzingFolders}
            className="w-full px-4 py-3 bg-foreground/8 hover:bg-foreground/12 disabled:bg-foreground/5 disabled:text-foreground/25 disabled:cursor-not-allowed text-foreground/80 font-medium rounded-xl transition-all flex items-center justify-center gap-2 border border-foreground/10"
          >
            {analyzingFolders ? (
              <><RefreshCw className="w-4 h-4 animate-spin" /> Analisando ZIP...</>
            ) : (
              <><Folder className="w-4 h-4" /> Analisar pastas do ZIP (opcional)</>
            )}
          </button>
        )}

        {/* Seleção de pastas */}
        {step === "folders" && availableFolders.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-foreground/70">
                Pastas para apagar antes do commit
              </p>
              <button
                onClick={() => { setStep("form"); setAvailableFolders([]); setSelectedFolders(new Set()); setUploadedZipPath(null); }}
                className="text-xs text-foreground/40 hover:text-foreground/70 flex items-center gap-1 transition-colors"
              >
                <X className="w-3 h-3" /> Limpar
              </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {availableFolders.map((folder) => {
                const selected = selectedFolders.has(folder);
                return (
                  <button
                    key={folder}
                    onClick={() => toggleFolder(folder)}
                    className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border text-left transition-all ${
                      selected
                        ? "bg-red-500/10 border-red-500/40 text-red-400"
                        : "bg-foreground/5 border-foreground/10 text-foreground/70 hover:bg-foreground/10 hover:border-foreground/20"
                    }`}
                  >
                    {selected ? <FolderOpen className="w-3.5 h-3.5 flex-shrink-0" /> : <Folder className="w-3.5 h-3.5 flex-shrink-0" />}
                    <span className="text-xs font-mono truncate">{folder}</span>
                    {selected && <Trash2 className="w-3 h-3 ml-auto flex-shrink-0 opacity-70" />}
                  </button>
                );
              })}
            </div>
            {selectedFolders.size > 0 && (
              <div className="flex flex-wrap gap-2">
                {Array.from(selectedFolders).map((f) => (
                  <span key={f} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-red-500/10 text-red-400 text-xs font-mono rounded-lg border border-red-500/20">
                    <Trash2 className="w-3 h-3" />
                    {f}
                    <button onClick={() => toggleFolder(f)} className="ml-0.5 hover:text-red-300">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full px-4 py-3 bg-primary hover:bg-primary/90 disabled:bg-foreground/10 disabled:text-foreground/30 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all flex items-center justify-center gap-2"
        >
          {loading ? (
            <><RefreshCw className="w-5 h-5 animate-spin" /> Enviando...</>
          ) : (
            <><GitCommit className="w-5 h-5" />
              {selectedFolders.size > 0
                ? `Apagar ${selectedFolders.size} pasta(s) e realizar commit`
                : "Realizar Commit"}
            </>
          )}
        </button>
      </div>

      {result && (
        <div className={`bg-background/50 backdrop-blur-xl border rounded-xl p-6 ${result.success ? "border-green-500/20" : "border-red-500/20"}`}>
          <div className="flex items-center gap-2 mb-4">
            {result.success
              ? <CheckCircle className="w-5 h-5 text-green-500" />
              : <XCircle className="w-5 h-5 text-red-500" />}
            <h2 className="text-xl font-bold">
              {result.success ? `Commit realizado em ${result.data?.appName}` : "Erro no commit"}
            </h2>
          </div>
          {!result.success && result.message && (
            <p className="text-sm text-red-400 mb-4">{result.message}</p>
          )}
          {result.data?.warning && (
            <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-sm text-yellow-400">
              {result.data.warning}
            </div>
          )}
          {result.data?.logs?.length > 0 && (
            <div className="bg-black/50 rounded-lg p-4 max-h-64 overflow-y-auto font-mono text-sm">
              {result.data.logs.map((log: any, i: number) => (
                <div key={i} className="flex items-start gap-2 mb-2">
                  {log.type === "success" ? <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                    : log.type === "error" ? <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                    : log.type === "warning" ? <AlertCircle className="w-4 h-4 text-yellow-500 flex-shrink-0" />
                    : <Clock className="w-4 h-4 text-blue-500 flex-shrink-0" />}
                  <span className="text-foreground/50 text-xs shrink-0">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className={log.type === "success" ? "text-green-400" : log.type === "error" ? "text-red-400" : log.type === "warning" ? "text-yellow-400" : "text-foreground/70"}>{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB NAV
// ─────────────────────────────────────────────────────────────────────────────

type Tab = "mass" | "single" | "changelogs";

function TabButton({
  active,
  onClick,
  icon: Icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: any;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
        active
          ? "bg-primary text-white shadow-lg shadow-primary/20"
          : "text-foreground/55 hover:text-foreground hover:bg-foreground/5 border border-foreground/10"
      }`}
    >
      <Icon className="w-4 h-4" />
      {children}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PAGE EXPORT
// ─────────────────────────────────────────────────────────────────────────────

export default function UpdatesPage() {
  const [tab, setTab] = useState<Tab>("mass");

  return (
    <div className="p-6 space-y-6">
      {/* Sub-navigation */}
      <div className="flex items-center gap-3 pb-4 border-b border-foreground/10">
        <TabButton
          active={tab === "mass"}
          onClick={() => setTab("mass")}
          icon={Zap}
        >
          Atualizações em Massa
        </TabButton>
        <TabButton
          active={tab === "single"}
          onClick={() => setTab("single")}
          icon={GitCommit}
        >
          Commit Único
        </TabButton>
        <TabButton
          active={tab === "changelogs"}
          onClick={() => setTab("changelogs")}
          icon={FileText}
        >
          Changelogs
        </TabButton>
      </div>

      {tab === "mass" && <MassUpdateContent />}
      {tab === "single" && <SingleCommitContent />}
      {tab === "changelogs" && <ChangelogsSection />}
    </div>
  );
}
