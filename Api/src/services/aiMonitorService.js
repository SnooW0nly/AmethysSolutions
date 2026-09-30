/**
 * AI Monitor Service
 * Monitora aplicações na Discloud usando a CyM AI para análise inteligente
 * 
 * Fluxo:
 *  1. A cada POLL_INTERVAL, busca todas as apps ativas no banco
 *  2. Para cada app com hosting.appId, verifica status na Discloud
 *  3. Se offline: busca logs → envia pra CyM para análise
 *  4. CyM decide: reiniciar ou aguardar intervenção manual
 *  5. Salva relatório em .log e atualiza registros no banco
 *  6. Se RAM crítica (>85%): reinicia preventivamente
 */

import fetch from "node-fetch";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import discloudService from "./discloudService.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ─── Configurações ────────────────────────────────────────────────────────────

const POLL_INTERVAL_MS   = 2 * 60 * 1000;   // 2 minutoconst CYM_BASE_URL       = process.env.CYM_BASE_URL  || "https://apicym.stackr.lat";
const CYM_API_KEY        = process.env.CYM_API_KEY   || "";
const RAM_CRITICAL_PCT   = 0.85;             // 85% de uso = reinicia preventivamente
const LOG_DIR            = path.resolve(process.cwd(), "src/database/logs/ai-monitor");
const MAX_LOG_LINES      = 40;               // Máx de linhas de log buscadas da Discloud
const MAX_LOG_CHARS      = 3000;             // Máx de caracteres de log enviados pra CyM
const MAX_SUMMARY_EVENTS = 20;              // Máx de eventos no resumo da CyM

// ─── Padrões que indicam token inválido do Discord ───────────────────────────
const DISCORD_TOKEN_ERROR_PATTERNS = [
  /improper token/i,
  /invalid token/i,
  /401 unauthorized/i,
  /authentication failed/i,
  /token has been invalidated/i,
  /loginFailure/i,
  /LoginFailure/i,
  /discord.*401/i,
  /invalid authentication/i,
  /token.*invalid/i,
  /INVALID_TOKEN/i,
  /discord.errors.LoginFailure/i,
  /aiohttp.ClientResponseError.*401/i,
];

// ─── Garante que o diretório de logs existe ───────────────────────────────────

function ensureLogDir() {
  if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR, { recursive: true });
  }
}

// ─── Logger para arquivo ──────────────────────────────────────────────────────

function writeLog(entry) {
  ensureLogDir();

  const today = new Date().toISOString().split("T")[0]; // YYYY-MM-DD
  const logFile = path.join(LOG_DIR, `monitor-${today}.log`);

  const line = `[${new Date().toISOString()}] ${JSON.stringify(entry)}\n`;

  fs.appendFileSync(logFile, line, "utf8");
  console.log(`[AI-MONITOR] ${entry.level || "INFO"} | ${entry.message || JSON.stringify(entry)}`);
}

// ─── Chamada à CyM AI ─────────────────────────────────────────────────────────

async function callCyM(prompt, systemPrompt) {
  if (!CYM_API_KEY) {
    console.warn("[AI-MONITOR] CYM_API_KEY não configurada, usando fallback lógico");
    return null;
  }

  try {
    const response = await fetch(`${CYM_BASE_URL}/api/ai/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": CYM_API_KEY,
      },
      body: JSON.stringify({
        model: "CyM Pro",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user",   content: prompt },
        ],
      }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      console.error(`[AI-MONITOR] CyM retornou ${response.status}: ${text.slice(0, 200)}`);
      return null;
    }

    const data = await response.json();
    return data?.reply?.trim() || null;
  } catch (err) {
    console.error("[AI-MONITOR] Erro ao chamar CyM:", err.message);
    return null;
  }
}

// ─── Verifica se as logs indicam token inválido do Discord ───────────────────

function hasDiscordTokenError(logs) {
  if (!logs) return false;
  const combined = Array.isArray(logs) ? logs.join("\n") : logs;
  return DISCORD_TOKEN_ERROR_PATTERNS.some((pattern) => pattern.test(combined));
}

// ─── Busca logs da Discloud ─────────────────────────────────────────────────────

async function fetchDiscloudLogs(appId) {
  try {
    const result = await discloudService.getAppLogs(appId);
    if (!result.success) return "";
    return result.logs || "";
  } catch (err) {
    console.warn(`[AI-MONITOR] Não foi possível buscar logs de ${appId}:`, err.message);
    return "";
  }
}

// ─── Busca stats (RAM/CPU) da Discloud ─────────────────────────────────────────

async function fetchDiscloudStats(appId) {
  try {
    const result = await discloudService.getAppStatus(appId);
    if (!result.success) return null;
    return result.status;
  } catch (err) {
    console.warn(`[AI-MONITOR] fetchDiscloudStats erro para ${appId}: ${err.message}`);
    return null;
  }
}

// ─── Busca status atual de uma app na Discloud ─────────────────────────────────

async function fetchDiscloudStatus(appId) {
  try {
    const result = await discloudService.getAppStatus(appId);
    if (!result.success) return null;
    return result.status?.container || null;
  } catch (err) {
    console.warn(`[AI-MONITOR] fetchDiscloudStatus erro para ${appId}: ${err.message}`);
    return null;
  }
}

// ─── Reinicia app na Discloud ───────────────────────────────────────────────────

async function restartDiscloudApp(appId) {
  try {
    const result = await discloudService.restartApp(appId);
    return result.success;
  } catch (err) {
    console.error(`[AI-MONITOR] Erro ao reiniciar ${appId}:`, err.message);
    return false;
  }
}

// ─── Liga app na Discloud ───────────────────────────────────────────────────────

async function startDiscloudApp(appId) {
  try {
    const result = await discloudService.startApp(appId);
    return result.success;
  } catch (err) {
    console.error(`[AI-MONITOR] Erro ao ligar ${appId}:`, err.message);
    return false;
  }
}

// ─── Parseia uso de RAM de strings como "135MiB / 256MiB" ────────────────────

function parseRamUsage(ramString) {
  if (!ramString) return null;

  const match = ramString.match(/(\d+(?:\.\d+)?)\s*MiB?\s*\/\s*(\d+(?:\.\d+)?)\s*MiB?/i);
  if (!match) return null;

  const used  = parseFloat(match[1]);
  const total = parseFloat(match[2]);
  return total > 0 ? { used, total, pct: used / total } : null;
}

// ─── Analisa logs com CyM AI ──────────────────────────────────────────────────

function sanitizeLogs(logs) {
  if (!logs) return "(sem logs disponíveis)";

  const lines = logs.split("\n");
  const cleaned = lines
    .slice(-MAX_LOG_LINES)
    .map(line => {
      let l = String(line).replace(/\d{4}-\d{2}-\d{2}T(\d{2}:\d{2}:\d{2})\.\d+Z/g, "$1");
      l = l.replace(/\/home\/[^\s]+\//g, ".../");
      l = l.replace(/\/app\/[^\s]+\//g, ".../");
      return l.trim();
    })
    .filter(Boolean)
    .filter(l => !/^\s*File ".*", line \d+$/.test(l));

  const joined = cleaned.join("\n");

  if (joined.length <= MAX_LOG_CHARS) return joined;

  return "...(truncado)\n" + joined.slice(-MAX_LOG_CHARS);
}

async function analyzeLogsWithCyM(appName, appId, logs, status) {
  const logsText = sanitizeLogs(logs);

  const systemPrompt = `Monitor de bots Discord na Discloud. Analise o log e responda com UMA linha de ação + diagnóstico curto.

AÇÕES (escolha exatamente uma):
ACTION:WAIT_TOKEN — token Discord inválido (LoginFailure, 401, improper token)
ACTION:RESTART    — erro recuperável (crash, ImportError, MemoryError, exit code)
ACTION:REPORT_ONLY — app online mas com erros nos logs
ACTION:WAIT       — não é possível determinar

Formato obrigatório (2 linhas no máximo):
ACTION:RESTART
Diagnóstico: <motivo em até 2 frases>`;

  const prompt = `App: ${appName} | Status: ${status}
Logs:
${logsText}`;

  const reply = await callCyM(prompt, systemPrompt);
  return reply;
}

// ─── Gera resumo diário com CyM AI ───────────────────────────────────────────

async function generateDailySummary(events) {
  if (!events || events.length === 0) return null;

  const compacted = events.slice(-MAX_SUMMARY_EVENTS).map(e => ({
    t:      e.timestamp ? e.timestamp.slice(11, 19) : "?",
    app:    e.appName   || e.appId || "?",
    action: e.action    || "?",
    msg:    (e.message  || "").slice(0, 80),
  }));

  const systemPrompt = `Monitor de bots Discord. Gere resumo executivo das últimas ações do monitor. Seja breve e profissional.`;
  const prompt = `Eventos:\n${JSON.stringify(compacted, null, 2)}`;

  return await callCyM(prompt, systemPrompt);
}

// ─── Estado interno do monitor ────────────────────────────────────────────────

const monitorState = {
  isRunning:    false,
  lastCycle:    null,
  cycleCount:   0,
  events:       [],           // Buffer de eventos do ciclo atual (últimas 500 entradas)
  appStates:    new Map(),    // appId → { status, lastCheck, waitingToken, restartCount }
  summary:      null,         // Último resumo gerado pela CyM
  summaryAt:    null,
};

// ─── Registra evento ──────────────────────────────────────────────────────────

function recordEvent(event) {
  const entry = { ...event, timestamp: new Date().toISOString() };
  monitorState.events.push(entry);

  // Mantém apenas os últimos 500 eventos em memória
  if (monitorState.events.length > 500) {
    monitorState.events.shift();
  }

  writeLog(entry);
}

// ─── Processa uma aplicação individual ────────────────────────────────────────

async function processApplication(app) {
  const dbId = String(app._id);
  const appId = app.hosting?.appId;
  const appName = app.name || "Sem nome";

  if (!appId) return;

  try {
    const prevState = monitorState.appStates.get(dbId) || {
      status:       "unknown",
      lastCheck:    null,
      waitingToken: false,
      restartCount: 0,
    };

    // 1. Busca status na Discloud
    const currentStatus = await fetchDiscloudStatus(appId);
    if (!currentStatus) return;

    // 2. Se estava aguardando token, verifica se mudou algo (opcional)
    if (prevState.waitingToken) {
      // Se voltou a ficar online, limpa a flag
      if (currentStatus === "online" || currentStatus === "running") {
        monitorState.appStates.set(dbId, { ...prevState, waitingToken: false, status: currentStatus });
      }
      return;
    }

    // 3. Verifica RAM crítica
    const stats = await fetchDiscloudStats(appId);
    const ram = parseRamUsage(stats?.memory);

    if (ram && ram.pct >= RAM_CRITICAL_PCT) {
      recordEvent({
        level:    "WARN",
        appId:    dbId,
        appName,
        discloudId: appId,
        message:  `RAM crítica detectada (${(ram.pct * 100).toFixed(1)}%) — reiniciando preventivamente`,
        action:   "RAM_RESTART",
      });
      await restartDiscloudApp(appId);
      return;
    }

    // 4. Se estiver offline/crashado, analisa logs
    const isOffline = ["offline", "exited", "crashed", "error"].includes(currentStatus);
    if (!isOffline) {
      // Apenas atualiza estado
      monitorState.appStates.set(dbId, {
        ...prevState,
        status:    currentStatus,
        lastCheck: new Date().toISOString(),
      });
      return;
    }

    // 5. Busca logs
    const logs = await fetchDiscloudLogs(appId);

    // 6. Análise rápida de token (fallback local)
    if (hasDiscordTokenError(logs)) {
      recordEvent({
        level:    "WARN",
        appId:    dbId,
        appName,
        discloudId: appId,
        message:  "Token Discord inválido detectado (análise local) — aguardando troca",
        action:   "WAIT_TOKEN",
      });
      monitorState.appStates.set(dbId, {
        ...prevState,
        status:       currentStatus,
        lastCheck:    new Date().toISOString(),
        waitingToken: true,
      });
      return;
    }

    // 7. Análise com CyM AI
    const aiReply = await analyzeLogsWithCyM(appName, appId, logs, currentStatus);
    if (!aiReply) {
      // Fallback: tenta apenas um restart se estiver offline
      await restartDiscloudApp(appId);
      return;
    }

    // 8. Parse da resposta da CyM
    const actionMatch = aiReply.match(/ACTION:(WAIT_TOKEN|RESTART|REPORT_ONLY|WAIT)/);
    const action = actionMatch ? actionMatch[1] : "WAIT";
    const aiDiagnosis = aiReply.split("\n").find(l => l.startsWith("Diagnóstico:")) || aiReply;

    // 9. Executa ação
    switch (action) {
      case "WAIT_TOKEN": {
        recordEvent({
          level:    "WARN",
          appId:    dbId,
          appName,
          discloudId: appId,
          message:  "CyM detectou token Discord inválido — aguardando troca manual",
          action:   "WAIT_TOKEN",
          aiAnalysis: aiDiagnosis,
        });

        monitorState.appStates.set(dbId, {
          ...prevState,
          status:       currentStatus,
          lastCheck:    new Date().toISOString(),
          waitingToken: true,
        });
        break;
      }

      case "RESTART": {
        recordEvent({
          level:    "INFO",
          appId:    dbId,
          appName,
          discloudId: appId,
          message:  "CyM decidiu reiniciar a aplicação",
          action:   "RESTARTING",
          aiAnalysis: aiDiagnosis,
        });

        // Tenta restart primeiro, senão start
        let success = await restartDiscloudApp(appId);
        if (!success) {
          success = await startDiscloudApp(appId);
        }

        recordEvent({
          level:    success ? "INFO" : "ERROR",
          appId:    dbId,
          appName,
          discloudId: appId,
          message:  success
            ? "Aplicação reiniciada com sucesso pela IA"
            : "Falha ao reiniciar a aplicação",
          action:   success ? "RESTARTED" : "RESTART_FAILED",
          aiAnalysis: aiDiagnosis,
        });

        monitorState.appStates.set(dbId, {
          ...prevState,
          status:        currentStatus,
          lastCheck:     new Date().toISOString(),
          waitingToken:  false,
          restartCount:  prevState.restartCount + (success ? 1 : 0),
          lastRestartAt: success ? new Date().toISOString() : prevState.lastRestartAt,
        });
        break;
      }

      case "REPORT_ONLY": {
        recordEvent({
          level:    "INFO",
          appId:    dbId,
          appName,
          discloudId: appId,
          message:  "CyM: apenas reportando — app online com erros nos logs",
          action:   "REPORT_ONLY",
          aiAnalysis: aiDiagnosis,
        });

        monitorState.appStates.set(dbId, {
          ...prevState,
          status:    currentStatus,
          lastCheck: new Date().toISOString(),
        });
        break;
      }

      default: {
        recordEvent({
          level:    "INFO",
          appId:    dbId,
          appName,
          discloudId: appId,
          message:  "CyM aguardando — sem ação no momento",
          action:   "WAIT",
          aiAnalysis: aiDiagnosis,
        });

        monitorState.appStates.set(dbId, {
          ...prevState,
          status:    currentStatus,
          lastCheck: new Date().toISOString(),
        });
        break;
      }
    }
  } catch (err) {
    recordEvent({
      level:    "ERROR",
      appId:    dbId,
      appName,
      discloudId: appId,
      message:  `Erro interno ao processar app: ${err.message}`,
      action:   "ERROR",
    });
  }
}

// ─── Ciclo principal de monitoramento ────────────────────────────────────────

async function runMonitorCycle() {
  if (monitorState.isRunning) {
    console.log("[AI-MONITOR] Ciclo anterior ainda em execução, pulando...");
    return;
  }

  monitorState.isRunning  = true;
  monitorState.lastCycle  = new Date().toISOString();
  monitorState.cycleCount += 1;

  console.log(`[AI-MONITOR] Iniciando ciclo #${monitorState.cycleCount}`);

  try {
    // Importa Application dinamicamente para evitar problemas de circular dependency
    const { default: Application } = await import("../database/models/Application.js");

    const apps = await Application.find({
      isDeleted: false,
      isBlocked: false,
      "hosting.appId": { $exists: true, $ne: null, $ne: "" },
    })
      .select("_id name hosting bot botID")
      .lean();

    console.log(`[AI-MONITOR] ${apps.length} aplicações para monitorar`);

    // Processa em paralelo com limite de concorrência (5 por vez)
    const BATCH_SIZE = 5;
    for (let i = 0; i < apps.length; i += BATCH_SIZE) {
      const batch = apps.slice(i, i + BATCH_SIZE);
      await Promise.allSettled(batch.map((app) => processApplication(app)));

      // Pequena pausa entre batches para não sobrecarregar a API da Discloud
      if (i + BATCH_SIZE < apps.length) {
        await new Promise((r) => setTimeout(r, 2000));
      }
    }

    // Gera resumo com CyM a cada 12 ciclos (~24min) ou se houver muitos eventos
    const shouldGenerateSummary =
      monitorState.cycleCount % 12 === 0 ||
      monitorState.events.filter(
        (e) => e.action === "RESTARTED" || e.action === "WAIT_TOKEN"
      ).length > 5;

    if (shouldGenerateSummary) {
      console.log("[AI-MONITOR] Gerando resumo com CyM...");
      const recentEvents = monitorState.events.slice(-100);
      const summary = await generateDailySummary(recentEvents);

      if (summary) {
        monitorState.summary   = summary;
        monitorState.summaryAt = new Date().toISOString();

        writeLog({
          level:   "SUMMARY",
          message: "Resumo gerado pela CyM",
          summary,
        });
      }
    }

    console.log(`[AI-MONITOR] Ciclo #${monitorState.cycleCount} concluído — ${apps.length} apps verificadas`);
  } catch (err) {
    console.error("[AI-MONITOR] Erro no ciclo principal:", err.message);
    recordEvent({
      level:   "ERROR",
      message: `Erro no ciclo principal: ${err.message}`,
      action:  "CYCLE_ERROR",
    });
  } finally {
    monitorState.isRunning = false;
  }
}

// ─── API pública do serviço ───────────────────────────────────────────────────

let _pollInterval = null;

export function startAIMonitor() {
  if (_pollInterval) {
    console.warn("[AI-MONITOR] Monitor já está rodando");
    return;
  }

  ensureLogDir();
  console.log(`[AI-MONITOR] Iniciando monitor (intervalo: ${POLL_INTERVAL_MS / 1000}s)`);

  // Primeiro ciclo após 10s (deixa o servidor estabilizar)
  setTimeout(runMonitorCycle, 10_000);

  _pollInterval = setInterval(runMonitorCycle, POLL_INTERVAL_MS);
}

export function stopAIMonitor() {
  if (_pollInterval) {
    clearInterval(_pollInterval);
    _pollInterval = null;
    console.log("[AI-MONITOR] Monitor parado");
  }
}

export function getMonitorState() {
  return {
    isRunning:  monitorState.isRunning,
    lastCycle:  monitorState.lastCycle,
    cycleCount: monitorState.cycleCount,
    summary:    monitorState.summary,
    summaryAt:  monitorState.summaryAt,
    appStates:  Object.fromEntries(monitorState.appStates),
    recentEvents: monitorState.events.slice(-200),
    stats: {
      total:         monitorState.appStates.size,
      waitingToken:  [...monitorState.appStates.values()].filter((s) => s.waitingToken).length,
      restarted:     monitorState.events.filter((e) => e.action === "RESTARTED").length,
      errors:        monitorState.events.filter((e) => e.level === "ERROR").length,
    },
  };
}

export function getLogFiles() {
  ensureLogDir();
  try {
    return fs.readdirSync(LOG_DIR)
      .filter((f) => f.endsWith(".log"))
      .sort()
      .reverse()
      .map((f) => ({
        name: f,
        path: path.join(LOG_DIR, f),
        size: fs.statSync(path.join(LOG_DIR, f)).size,
        date: f.replace("monitor-", "").replace(".log", ""),
      }));
  } catch {
    return [];
  }
}

export function readLogFile(filename) {
  ensureLogDir();
  const safeName = path.basename(filename); // sanitiza
  const filePath = path.join(LOG_DIR, safeName);

  if (!fs.existsSync(filePath)) return null;

  try {
    const content = fs.readFileSync(filePath, "utf8");
    return content
      .split("\n")
      .filter(Boolean)
      .map((line) => {
        const match = line.match(/^\[(.+?)\] (.+)$/);
        if (!match) return null;
        try {
          return { timestamp: match[1], ...JSON.parse(match[2]) };
        } catch {
          return { timestamp: match[1], raw: match[2] };
        }
      })
      .filter(Boolean)
      .reverse(); // mais recentes primeiro
  } catch {
    return null;
  }
}

// Força um ciclo imediato (para o endpoint de "forçar análise")
export async function forceMonitorCycle() {
  await runMonitorCycle();
  return getMonitorState();
}

// Limpa o estado de "aguardando token" de uma app específica
// (chamado quando admin confirma que token foi trocado)
export function clearWaitingTokenState(dbAppId) {
  const state = monitorState.appStates.get(dbAppId);
  if (state) {
    monitorState.appStates.set(dbAppId, { ...state, waitingToken: false });
    recordEvent({
      level:   "INFO",
      appId:   dbAppId,
      message: "Estado 'aguardando token' limpo manualmente pelo admin",
      action:  "TOKEN_CLEARED",
    });
    return true;
  }
  return false;
}
