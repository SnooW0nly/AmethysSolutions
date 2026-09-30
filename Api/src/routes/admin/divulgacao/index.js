/**
 * src/routes/admin/divulgacao/index.js
 *
 * Rotas REST para o sistema de divulgação (Selfbot).
 * Registre em src/routes/admin/index.js:
 *   import divulgacaoAdminRoute from "./divulgacao/index.js";
 *   router.use("/divulgacao", divulgacaoAdminRoute);
 */

import { Router } from "express";
import { v4 as uuidv4 } from "uuid";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import Divulgacao from "../../../database/models/Divulgacao.js";
import {
  validateToken,
  fetchChannel,
  startService,
  stopService,
  isRunning,
  getLogs,
} from "../../../services/divulgacaoService.js";

const router = Router();
router.use(authMiddleware, requireAdmin);

// ── Helper: pega ou cria o documento único ─────────────────────────────────

async function getConfig() {
  let cfg = await Divulgacao.findOne();
  if (!cfg) cfg = await Divulgacao.create({});
  return cfg;
}

// ─────────────────────────────────────────────────────────────────────────────
// GET /api/admin/divulgacao
// Retorna toda a config (tokens com token mascarado)
// ─────────────────────────────────────────────────────────────────────────────
router.get("/", async (req, res) => {
  try {
    const cfg = await getConfig();
    const data = cfg.toObject();

    // Mascara tokens por segurança
    data.tokens = data.tokens.map((t) => ({
      ...t,
      token: maskToken(t.token),
    }));

    res.json({ success: true, config: data, isRunning: isRunning() });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// PUT /api/admin/divulgacao/message
// Atualiza APENAS a mensagem (não existe mais embedConfig)
// ─────────────────────────────────────────────────────────────────────────────
router.put("/message", async (req, res) => {
  try {
    const { message } = req.body;
    const update = { updatedBy: req.user._id };
    if (message !== undefined) update.message = message;

    const cfg = await Divulgacao.findOneAndUpdate(
      {},
      { $set: update },
      { new: true, upsert: true }
    );

    res.json({ success: true, message: cfg.message });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /api/admin/divulgacao/tokens
// Adiciona um novo token de CONTA (user token)
// ─────────────────────────────────────────────────────────────────────────────
router.post("/tokens", async (req, res) => {
  try {
    const { token, label } = req.body;
    if (!token) return res.status(400).json({ error: "token é obrigatório" });

    // Valida token de usuário (não bot)
    const info = await validateToken(token);
    if (!info.valid) {
      return res.status(400).json({ error: "Token Discord inválido ou sem permissão" });
    }

    const cfg = await getConfig();

    // Verifica duplicata
    const exists = cfg.tokens.some((t) => t.token === token);
    if (exists) return res.status(409).json({ error: "Token já cadastrado" });

    const newToken = {
      id: uuidv4(),
      label: label || info.username || "",
      token,
      isValid: true,
      lastValidatedAt: new Date(),
      username: info.username,
      userId: info.userId,
      avatar: info.avatar,
      channels: [],
      isActive: true,
    };

    cfg.tokens.push(newToken);
    await cfg.save();

    res.json({
      success: true,
      token: { ...newToken, token: maskToken(token) },
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// DELETE /api/admin/divulgacao/tokens/:tokenId
// Remove um token
// ─────────────────────────────────────────────────────────────────────────────
router.delete("/tokens/:tokenId", async (req, res) => {
  try {
    const { tokenId } = req.params;
    await Divulgacao.updateOne({}, { $pull: { tokens: { id: tokenId } } });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// PATCH /api/admin/divulgacao/tokens/:tokenId
// Atualiza label ou isActive de um token
// ─────────────────────────────────────────────────────────────────────────────
router.patch("/tokens/:tokenId", async (req, res) => {
  try {
    const { tokenId } = req.params;
    const { label, isActive } = req.body;

    const setFields = {};
    if (label !== undefined) setFields["tokens.$.label"] = label;
    if (isActive !== undefined) setFields["tokens.$.isActive"] = isActive;

    await Divulgacao.updateOne(
      { "tokens.id": tokenId },
      { $set: setFields }
    );

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST|PATCH /api/admin/divulgacao/tokens/:tokenId/rotate-token
// Troca o token de uma conta já cadastrada por um novo token
// ─────────────────────────────────────────────────────────────────────────────
const rotateTokenHandler = async (req, res) => {
  try {
    const { tokenId } = req.params;
    const { newToken } = req.body;

    if (!newToken) return res.status(400).json({ error: "newToken é obrigatório" });

    const cfg = await getConfig();
    const tokenCfg = cfg.tokens.find((t) => t.id === tokenId);
    if (!tokenCfg) return res.status(404).json({ error: "Conta não encontrada" });

    // Verifica se o novo token já está sendo usado por outra conta
    const duplicate = cfg.tokens.find((t) => t.token === newToken && t.id !== tokenId);
    if (duplicate) return res.status(409).json({ error: "Este token já está cadastrado em outra conta" });

    // Valida o novo token no Discord antes de salvar
    const info = await validateToken(newToken);
    if (!info.valid) {
      return res.status(400).json({ error: "Novo token Discord inválido ou sem permissão" });
    }

    await Divulgacao.updateOne(
      { "tokens.id": tokenId },
      {
        $set: {
          "tokens.$.token": newToken,
          "tokens.$.isValid": true,
          "tokens.$.lastValidatedAt": new Date(),
          "tokens.$.username": info.username || tokenCfg.username,
          "tokens.$.userId": info.userId || tokenCfg.userId,
          "tokens.$.avatar": info.avatar || tokenCfg.avatar,
        },
      }
    );

    res.json({
      success: true,
      message: "Token atualizado com sucesso",
      token: maskToken(newToken),
      username: info.username,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

router.post("/tokens/:tokenId/rotate-token", rotateTokenHandler);
router.patch("/tokens/:tokenId/rotate-token", rotateTokenHandler);

// ─────────────────────────────────────────────────────────────────────────────
// POST /api/admin/divulgacao/tokens/:tokenId/validate
// Revalida um token (agora retorna dados da conta)
// ─────────────────────────────────────────────────────────────────────────────
router.post("/tokens/:tokenId/validate", async (req, res) => {
  try {
    const { tokenId } = req.params;
    const cfg = await getConfig();
    const tokenCfg = cfg.tokens.find((t) => t.id === tokenId);
    if (!tokenCfg) return res.status(404).json({ error: "Token não encontrado" });

    const info = await validateToken(tokenCfg.token);

    await Divulgacao.updateOne(
      { "tokens.id": tokenId },
      {
        $set: {
          "tokens.$.isValid": info.valid,
          "tokens.$.lastValidatedAt": new Date(),
          "tokens.$.username": info.username || tokenCfg.username,
          "tokens.$.userId": info.userId || tokenCfg.userId,
          "tokens.$.avatar": info.avatar || tokenCfg.avatar,
        },
      }
    );

    res.json({ success: true, valid: info.valid, ...info });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /api/admin/divulgacao/tokens/:tokenId/channels
// Adiciona um canal a um token
// ─────────────────────────────────────────────────────────────────────────────
router.post("/tokens/:tokenId/channels", async (req, res) => {
  try {
    const { tokenId } = req.params;
    const { channelId } = req.body;
    if (!channelId) return res.status(400).json({ error: "channelId é obrigatório" });

    const cfg = await getConfig();
    const tokenCfg = cfg.tokens.find((t) => t.id === tokenId);
    if (!tokenCfg) return res.status(404).json({ error: "Token não encontrado" });

    // Verifica duplicata
    if (tokenCfg.channels.some((c) => c.channelId === channelId)) {
      return res.status(409).json({ error: "Canal já cadastrado neste token" });
    }

    // Busca info do canal via Discord API (user token)
    let channelInfo = { id: channelId, name: channelId, rate_limit_per_user: 0, guild_id: null };
    try {
      const info = await fetchChannel(tokenCfg.token, channelId);
      channelInfo = info;
    } catch (err) {
      return res.status(400).json({
        error: `Não foi possível acessar o canal ${channelId}: ${err.message}`,
      });
    }

    const newChannel = {
      channelId,
      channelName: channelInfo.name || channelId,
      guildId: channelInfo.guild_id || "",
      guildName: "",
      slowmode: channelInfo.rate_limit_per_user || 0,
      lastSentAt: null,
      lastMessageId: null,
      enabled: true,
    };

    await Divulgacao.updateOne(
      { "tokens.id": tokenId },
      { $push: { "tokens.$.channels": newChannel } }
    );

    res.json({ success: true, channel: newChannel });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// DELETE /api/admin/divulgacao/tokens/:tokenId/channels/:channelId
// Remove um canal de um token
// ─────────────────────────────────────────────────────────────────────────────
router.delete("/tokens/:tokenId/channels/:channelId", async (req, res) => {
  try {
    const { tokenId, channelId } = req.params;

    await Divulgacao.updateOne(
      { "tokens.id": tokenId },
      { $pull: { "tokens.$.channels": { channelId } } }
    );

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// PATCH /api/admin/divulgacao/tokens/:tokenId/channels/:channelId
// Atualiza config de um canal (enabled, slowmode)
// ─────────────────────────────────────────────────────────────────────────────
router.patch("/tokens/:tokenId/channels/:channelId", async (req, res) => {
  try {
    const { tokenId, channelId } = req.params;
    const { enabled, slowmode } = req.body;

    const setFields = {};
    if (enabled !== undefined)  setFields["tokens.$[t].channels.$[c].enabled"]  = enabled;
    if (slowmode !== undefined) setFields["tokens.$[t].channels.$[c].slowmode"] = slowmode;

    await Divulgacao.updateOne(
      {},
      { $set: setFields },
      { arrayFilters: [{ "t.id": tokenId }, { "c.channelId": channelId }] }
    );

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /api/admin/divulgacao/tokens/:sourceTokenId/copy-channels/:destTokenId
// Copia a config de canais de um token para outro
// ─────────────────────────────────────────────────────────────────────────────
router.post("/tokens/:sourceTokenId/copy-channels/:destTokenId", async (req, res) => {
  try {
    const { sourceTokenId, destTokenId } = req.params;
    const { overwrite = false } = req.body;

    const cfg = await getConfig();
    const source = cfg.tokens.find((t) => t.id === sourceTokenId);
    const dest   = cfg.tokens.find((t) => t.id === destTokenId);

    if (!source) return res.status(404).json({ error: "Token de origem não encontrado" });
    if (!dest)   return res.status(404).json({ error: "Token de destino não encontrado" });

    let channelsToAdd;
    if (overwrite) {
      channelsToAdd = source.channels.map((c) => ({ ...c }));
    } else {
      const existingIds = new Set(dest.channels.map((c) => c.channelId));
      channelsToAdd = source.channels
        .filter((c) => !existingIds.has(c.channelId))
        .map((c) => ({ ...c }));
    }

    if (overwrite) {
      await Divulgacao.updateOne(
        { "tokens.id": destTokenId },
        { $set: { "tokens.$.channels": channelsToAdd } }
      );
    } else {
      if (channelsToAdd.length > 0) {
        await Divulgacao.updateOne(
          { "tokens.id": destTokenId },
          { $push: { "tokens.$.channels": { $each: channelsToAdd } } }
        );
      }
    }

    res.json({
      success: true,
      added: channelsToAdd.length,
      message: `${channelsToAdd.length} canal(is) copiado(s) para ${dest.label || dest.username}`,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /api/admin/divulgacao/start
// ─────────────────────────────────────────────────────────────────────────────
router.post("/start", async (req, res) => {
  try {
    if (isRunning()) return res.json({ success: true, message: "Já está rodando" });
    await startService();
    res.json({ success: true, message: "Serviço iniciado" });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /api/admin/divulgacao/stop
// ─────────────────────────────────────────────────────────────────────────────
router.post("/stop", async (req, res) => {
  try {
    await stopService();
    res.json({ success: true, message: "Serviço parado" });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /api/admin/divulgacao/logs
// Retorna logs recentes (em memória)
// ─────────────────────────────────────────────────────────────────────────────
router.get("/logs", async (req, res) => {
  try {
    const { limit = 50 } = req.query;
    const logs = getLogs().slice(0, Number(limit));
    res.json({ success: true, logs, isRunning: isRunning() });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /api/admin/divulgacao/tokens/:tokenId/channels/:channelId/test
// Envia mensagem de teste em um canal específico (user token, sem embed)
// ─────────────────────────────────────────────────────────────────────────────
router.post("/tokens/:tokenId/channels/:channelId/test", async (req, res) => {
  try {
    const { tokenId, channelId } = req.params;
    const cfg = await getConfig();
    const tokenCfg = cfg.tokens.find((t) => t.id === tokenId);
    if (!tokenCfg) return res.status(404).json({ error: "Token não encontrado" });

    if (!cfg.message?.trim()) {
      return res.status(400).json({ error: "Configure uma mensagem antes de testar" });
    }

    const body = { content: cfg.message.trim() };

    const DISCORD_API = "https://discord.com/api/v9";
    const discordRes = await fetch(`${DISCORD_API}/channels/${channelId}/messages`, {
      method: "POST",
      headers: {
        Authorization: tokenCfg.token, // user token, sem "Bot"
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!discordRes.ok) {
      const err = await discordRes.json().catch(() => ({}));
      return res.status(400).json({ error: err.message || `Discord retornou ${discordRes.status}` });
    }

    res.json({ success: true, message: "Mensagem de teste enviada!" });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Helper ───────────────────────────────────────────────────────────────────

function maskToken(token) {
  if (!token || token.length < 10) return "***";
  return token.slice(0, 6) + "..." + token.slice(-4);
}

export default router;