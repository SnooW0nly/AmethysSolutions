/**
 * Rotas Admin — AI Monitor
 * GET  /api/admin/ai-monitor/state        → estado atual do monitor
 * GET  /api/admin/ai-monitor/events       → eventos recentes (com filtros)
 * GET  /api/admin/ai-monitor/summary      → resumo gerado pela CyM
 * POST /api/admin/ai-monitor/force-cycle  → força um ciclo agora
 * GET  /api/admin/ai-monitor/logs         → lista arquivos de log
 * GET  /api/admin/ai-monitor/logs/:file   → conteúdo de um arquivo de log
 * POST /api/admin/ai-monitor/clear-token/:appId → limpa estado "aguardando token"
 * POST /api/admin/ai-monitor/ask          → pergunta livre pra CyM sobre as apps
 */

import { Router } from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import {
  getMonitorState,
  getLogFiles,
  readLogFile,
  forceMonitorCycle,
  clearWaitingTokenState,
} from "../../../services/aiMonitorService.js";
import fetch from "node-fetch";

const router = Router();

router.use(authMiddleware, requireAdmin);

// ─── Estado atual ─────────────────────────────────────────────────────────────

router.get("/state", (req, res) => {
  try {
    const state = getMonitorState();
    res.json({ success: true, ...state });
  } catch (err) {
    res.status(500).json({ error: "Erro ao obter estado do monitor" });
  }
});

// ─── Eventos recentes (com filtros opcionais) ─────────────────────────────────

router.get("/events", (req, res) => {
  try {
    const state = getMonitorState();
    let events = state.recentEvents;

    const { appId, action, level, limit = 100 } = req.query;

    if (appId)  events = events.filter((e) => e.appId === appId);
    if (action) events = events.filter((e) => e.action === action);
    if (level)  events = events.filter((e) => e.level === level);

    events = events.slice(-parseInt(limit));

    res.json({ success: true, events, total: events.length });
  } catch (err) {
    res.status(500).json({ error: "Erro ao obter eventos" });
  }
});

// ─── Resumo da CyM ────────────────────────────────────────────────────────────

router.get("/summary", (req, res) => {
  try {
    const state = getMonitorState();
    res.json({
      success:   true,
      summary:   state.summary,
      summaryAt: state.summaryAt,
      stats:     state.stats,
    });
  } catch (err) {
    res.status(500).json({ error: "Erro ao obter resumo" });
  }
});

// ─── Força ciclo imediato ─────────────────────────────────────────────────────

router.post("/force-cycle", async (req, res) => {
  try {
    const state = await forceMonitorCycle();
    res.json({ success: true, message: "Ciclo forçado executado", ...state });
  } catch (err) {
    res.status(500).json({ error: `Erro ao forçar ciclo: ${err.message}` });
  }
});

// ─── Lista arquivos de log ────────────────────────────────────────────────────

router.get("/logs", (req, res) => {
  try {
    const files = getLogFiles();
    res.json({ success: true, files });
  } catch (err) {
    res.status(500).json({ error: "Erro ao listar logs" });
  }
});

// ─── Lê conteúdo de arquivo de log ───────────────────────────────────────────

router.get("/logs/:filename", (req, res) => {
  try {
    const { filename } = req.params;
    const { limit = 200 } = req.query;

    // Sanitiza: só aceita formato monitor-YYYY-MM-DD.log
    if (!/^monitor-\d{4}-\d{2}-\d{2}\.log$/.test(filename)) {
      return res.status(400).json({ error: "Nome de arquivo inválido" });
    }

    const entries = readLogFile(filename);
    if (!entries) {
      return res.status(404).json({ error: "Arquivo não encontrado" });
    }

    res.json({
      success: true,
      filename,
      entries: entries.slice(0, parseInt(limit)),
      total:   entries.length,
    });
  } catch (err) {
    res.status(500).json({ error: "Erro ao ler arquivo de log" });
  }
});

// ─── Limpa estado "aguardando token" ─────────────────────────────────────────

router.post("/clear-token/:appId", (req, res) => {
  try {
    const { appId } = req.params;
    const cleared = clearWaitingTokenState(appId);

    if (!cleared) {
      return res.status(404).json({ error: "App não encontrada no estado do monitor" });
    }

    res.json({ success: true, message: "Estado 'aguardando token' limpo com sucesso" });
  } catch (err) {
    res.status(500).json({ error: "Erro ao limpar estado" });
  }
});

// ─── Pergunta livre pra CyM sobre as apps (chat do painel) ───────────────────

router.post("/ask", async (req, res) => {
  try {
    const { question } = req.body;

    if (!question || typeof question !== "string") {
      return res.status(400).json({ error: "Campo 'question' obrigatório" });
    }

    const CYM_BASE_URL = process.env.CYM_BASE_URL || "https://apicym.stackr.lat";
    const CYM_API_KEY  = process.env.CYM_API_KEY  || "";

    if (!CYM_API_KEY) {
      return res.status(503).json({ error: "CyM não configurada (CYM_API_KEY ausente)" });
    }

    // Inclui contexto atual do monitor na pergunta
    const state = getMonitorState();
    const contextSummary = `
Estado atual do monitor:
- Ciclos executados: ${state.cycleCount}
- Último ciclo: ${state.lastCycle}
- Total de apps monitoradas: ${state.stats?.total || 0}
- Apps aguardando troca de token: ${state.stats?.waitingToken || 0}
- Total de reinicios feitos: ${state.stats?.restarted || 0}
- Erros registrados: ${state.stats?.errors || 0}

Últimos 20 eventos:
${JSON.stringify(state.recentEvents?.slice(-20), null, 2)}

Resumo mais recente da CyM:
${state.summary || "(nenhum ainda)"}
    `.trim();

    const response = await fetch(`${CYM_BASE_URL}/api/ai/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": CYM_API_KEY,
      },
      body: JSON.stringify({
        model: "CyM Pro",
        messages: [
          {
            role: "system",
            content: `Você é o assistente de operações do painel Amethys.
Você tem acesso ao estado atual do monitor de bots Discord.
Responda perguntas do admin de forma técnica, clara e objetiva.
NUNCA sugira deletar aplicações.
Use markdown quando necessário.`,
          },
          {
            role: "user",
            content: `Contexto do monitor:\n${contextSummary}\n\nPergunta: ${question}`,
          },
        ],
      }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      return res.status(502).json({ error: `CyM retornou ${response.status}: ${text.slice(0, 200)}` });
    }

    const data   = await response.json();
    const answer = data?.reply?.trim() || "Sem resposta da CyM.";

    res.json({ success: true, answer });
  } catch (err) {
    res.status(500).json({ error: `Erro ao consultar CyM: ${err.message}` });
  }
});

export default router;