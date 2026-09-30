import { Router } from "express";
import mongoose from "mongoose";
import Application from "../../../database/models/Application.js";
import BotConfig from "../../../database/models/BotConfig.js";
import auditService from "../../../services/auditService.js";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";

const router = Router();
router.use(authMiddleware, requireAdmin);

// ─── Schema para salvar configs de aviso ─────────────────────────────────────
const AvisoConfigSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    content: { type: String, default: "" },
    embeds: { type: mongoose.Schema.Types.Mixed, default: [] },
    components: { type: mongoose.Schema.Types.Mixed, default: [] },
    flags: { type: Number, default: null },
    createdBy: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
    lastSentAt: { type: Date, default: null },
    lastSentStats: { type: mongoose.Schema.Types.Mixed, default: null },
  },
  { timestamps: true }
);

const AvisoConfig =
  mongoose.models.AvisoConfig ||
  mongoose.model("AvisoConfig", AvisoConfigSchema);

// ─── GET /api/admin/avisos/configs ───────────────────────────────────────────
router.get("/configs", async (req, res) => {
  try {
    const configs = await AvisoConfig.find({})
      .sort({ updatedAt: -1 })
      .lean();
    res.json({ success: true, configs });
  } catch (err) {
    console.error("[AVISOS] Erro ao listar configs:", err);
    res.status(500).json({ error: "Erro ao listar configs" });
  }
});

// ─── POST /api/admin/avisos/configs ──────────────────────────────────────────
router.post("/configs", async (req, res) => {
  try {
    const { name, content, embeds, components, flags } = req.body;
    const adminId = req.user?._id;

    if (!name?.trim()) {
      return res.status(400).json({ error: "Nome obrigatório" });
    }

    const config = await AvisoConfig.create({
      name: name.trim(),
      content: content || "",
      embeds: embeds || [],
      components: components || [],
      flags: flags || null,
      createdBy: adminId,
    });

    res.status(201).json({ success: true, config });
  } catch (err) {
    console.error("[AVISOS] Erro ao criar config:", err);
    res.status(500).json({ error: "Erro ao criar config" });
  }
});

// ─── PUT /api/admin/avisos/configs/:id ───────────────────────────────────────
router.put("/configs/:id", async (req, res) => {
  try {
    const { id } = req.params;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ error: "ID inválido" });
    }

    const { name, content, embeds, components, flags } = req.body;

    const config = await AvisoConfig.findByIdAndUpdate(
      id,
      { name, content, embeds, components, flags },
      { new: true }
    );

    if (!config) return res.status(404).json({ error: "Config não encontrada" });

    res.json({ success: true, config });
  } catch (err) {
    console.error("[AVISOS] Erro ao atualizar config:", err);
    res.status(500).json({ error: "Erro ao atualizar config" });
  }
});

// ─── DELETE /api/admin/avisos/configs/:id ────────────────────────────────────
router.delete("/configs/:id", async (req, res) => {
  try {
    const { id } = req.params;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ error: "ID inválido" });
    }

    await AvisoConfig.findByIdAndDelete(id);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: "Erro ao deletar config" });
  }
});

// ─── POST /api/admin/avisos/send ─────────────────────────────────────────────
/**
 * Envia DM para todos os owners de bots ativos.
 * Body: { configId?, payload: { content, embeds, components, flags } }
 * Usa o token de cada bot do cliente para enviar DM ao owner via Discord API.
 */
router.post("/send", async (req, res) => {
  try {
    const { configId, payload, targetFilter = "all" } = req.body;
    const adminId = String(req.user?._id || "");

    if (!payload || (!payload.content && !payload.embeds?.length)) {
      return res.status(400).json({ error: "Payload vazio — defina content ou embeds" });
    }

    // Busca todas as aplicações ativas (não deletadas, não bloqueadas)
    const appsQuery = { isDeleted: false, isBlocked: false };
    if (targetFilter === "active") {
      appsQuery.expiresAt = { $gte: new Date() };
    } else if (targetFilter === "expired") {
      appsQuery.expiresAt = { $lt: new Date() };
    }

    const apps = await Application.find(appsQuery)
      .select("botID bot.owner bot.token hosting.appId name")
      .lean();

    console.log(`[AVISOS SEND] ${apps.length} aplicações encontradas (filtro: ${targetFilter})`);

    const results = {
      total: apps.length,
      sent: 0,
      failed: 0,
      skipped: 0,
      errors: [],
    };

    // Para cada app, busca o token no BotConfig (mais atualizado) ou usa o da app
    const botIDs = apps.map((a) => a.botID).filter(Boolean);
    const botConfigs = await BotConfig.find({ botID: { $in: botIDs } })
      .select("botID bot.token bot.owner")
      .lean();

    const configMap = {};
    for (const bc of botConfigs) {
      configMap[bc.botID] = bc;
    }

    // Deduplica por owner (não manda 2x para o mesmo dono)
    const sentOwners = new Set();

    for (const app of apps) {
      try {
        const bc = configMap[app.botID];
        const token = bc?.bot?.token || app.bot?.token;
        const owner = bc?.bot?.owner || app.bot?.owner;

        if (!token || !owner) {
          results.skipped++;
          continue;
        }

        if (sentOwners.has(owner)) {
          results.skipped++;
          continue;
        }

        // 1. Abre DM channel com o owner
        const dmRes = await fetch("https://discord.com/api/v10/users/@me/channels", {
          method: "POST",
          headers: {
            Authorization: `Bot ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ recipient_id: owner }),
        });

        if (!dmRes.ok) {
          const errText = await dmRes.text();
          results.failed++;
          results.errors.push({
            appName: app.name,
            owner,
            error: `DM channel: ${dmRes.status} ${errText.slice(0, 100)}`,
          });
          continue;
        }

        const dmChannel = await dmRes.json();

        // 2. Envia a mensagem no canal DM
        const msgBody = {};
        if (payload.content) msgBody.content = payload.content;
        if (payload.embeds?.length) msgBody.embeds = payload.embeds;
        if (payload.components?.length) msgBody.components = payload.components;
        if (payload.flags) msgBody.flags = payload.flags;

        const msgRes = await fetch(
          `https://discord.com/api/v10/channels/${dmChannel.id}/messages`,
          {
            method: "POST",
            headers: {
              Authorization: `Bot ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify(msgBody),
          }
        );

        if (!msgRes.ok) {
          const errText = await msgRes.text();
          results.failed++;
          results.errors.push({
            appName: app.name,
            owner,
            error: `Send msg: ${msgRes.status} ${errText.slice(0, 100)}`,
          });
          continue;
        }

        sentOwners.add(owner);
        results.sent++;

        // Rate limit gentil — 1 msg a cada 300ms
        await new Promise((r) => setTimeout(r, 300));
      } catch (err) {
        results.failed++;
        results.errors.push({ appName: app.name, error: err.message });
      }
    }

    // Atualiza stats na config se fornecida
    if (configId && mongoose.Types.ObjectId.isValid(configId)) {
      await AvisoConfig.findByIdAndUpdate(configId, {
        lastSentAt: new Date(),
        lastSentStats: results,
      });
    }

    await auditService.log("aviso", "send", adminId, configId || "manual", {
      targetFilter,
      total: results.total,
      sent: results.sent,
      failed: results.failed,
      skipped: results.skipped,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
    });

    console.log(
      `[AVISOS SEND] Concluído — enviado: ${results.sent}, falhou: ${results.failed}, pulado: ${results.skipped}`
    );

    res.json({ success: true, results });
  } catch (err) {
    console.error("[AVISOS SEND] Erro:", err);
    res.status(500).json({ error: "Erro ao enviar avisos" });
  }
});

export default router;