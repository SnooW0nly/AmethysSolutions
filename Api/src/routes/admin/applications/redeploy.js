// src/routes/admin/applications/redeploy.js
// Adicionar no router de applications (index.js)
//
// import redeployRoute from "./redeploy.js";
// router.use("/", redeployRoute);   ← adicionar logo após as outras rotas
//
// OU simplesmente colar o handler diretamente no index.js de applications.

import { Router } from "express";
import mongoose from "mongoose";
import Application from "../../../database/models/Application.js";
import Plan from "../../../database/models/Plan.js";
import BotConfig from "../../../database/models/BotConfig.js";
import { deployBotWithConfig } from "../../../services/botDeployment.js";
import auditService from "../../../services/auditService.js";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import path from "path";
import fs from "fs";

const router = Router();

router.use(authMiddleware, requireAdmin);

/**
 * POST /api/admin/applications/:id/redeploy
 *
 * Faz o deploy de uma aplicação que já existe no banco mas não tem appId na Discloud.
 * Mantém todos os dados da aplicação (userId, plano, expiração, bot config, etc.).
 * Apenas atualiza o campo `hosting` com as infos da Discloud após o deploy.
 *
 * Casos de uso:
 *   - Deploy falhou durante a criação original
 *   - App foi deletada da Discloud manualmente mas permanece no banco
 *   - Migração de provider
 */
router.post("/:id/redeploy", async (req, res) => {
  try {
    const { id } = req.params;
    const adminId = String(req.user?._id || "");

    // Valida ObjectId
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ error: "ID inválido" });
    }

    // Busca a aplicação
    const application = await Application.findById(id).populate(
      "userId",
      "discordId username"
    );

    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    if (application.isDeleted) {
      return res.status(400).json({
        error: "Aplicação está deletada. Restaure-a antes de fazer redeploy.",
      });
    }

    // Aviso (não bloqueio): permite redeploy mesmo com appId caso o admin queira forçar
    const alreadyDeployed = !!application.hosting?.appId;

    // Resolve o plano para achar o ZIP
    const planId = application.plan?.id;
    if (!planId) {
      return res.status(400).json({ error: "Aplicação sem plano definido" });
    }

    const plan = await Plan.findOne({ id: planId }).lean();
    if (!plan) {
      return res.status(404).json({ error: `Plano '${planId}' não encontrado` });
    }
    if (!plan.zipFilename) {
      return res.status(400).json({
        error: `Plano '${plan.name}' não tem ZIP cadastrado. Faça upload do ZIP no painel de planos.`,
      });
    }

    // Localiza o ZIP no disco
    const zipPath = path.resolve(
      process.cwd(),
      "src/database/zip",
      plan.zipFilename
    );

    if (!fs.existsSync(zipPath)) {
      return res.status(400).json({
        error: `ZIP do plano não encontrado em disco: ${plan.zipFilename}. Faça o re-upload.`,
      });
    }

    // Owner do bot: prioridade → bot.owner → userId.discordId
    const ownerDiscordId =
      application.bot?.owner ||
      application.userId?.discordId ||
      "";

    const botID = application.botID;
    if (!botID) {
      return res.status(400).json({ error: "Aplicação sem botID. Isso não deveria acontecer." });
    }

    console.log(
      `[ADMIN REDEPLOY] Iniciando redeploy — app: ${id}, botID: ${botID}, plano: ${planId}, owner: ${ownerDiscordId}`
    );

    // ── Deploy na Discloud ──────────────────────────────────────────────────────
    let deployResult;
    try {
      deployResult = await deployBotWithConfig(
        zipPath,
        botID,
        ownerDiscordId,
        plan.version || null
      );
    } catch (deployErr) {
      console.error("[ADMIN REDEPLOY] Erro no deploy:", deployErr);
      return res.status(502).json({
        error: `Erro ao fazer deploy na Discloud: ${deployErr.message}`,
      });
    }

    const discloudResponse = deployResult.discloudResponse;
    const newAppId = deployResult.appId;

    if (!newAppId) {
      console.warn(
        "[ADMIN REDEPLOY] Deploy concluído mas Discloud não retornou appId. Resposta:",
        JSON.stringify(discloudResponse)
      );
    }

    // ── Atualiza somente o hosting no banco ───────────────────────────────────
    const now = new Date();
    const newHosting = {
      provider: "discloud",
      appId: newAppId ? String(newAppId) : application.hosting?.appId || "",
      name: discloudResponse?.name || application.hosting?.name || null,
      ram: discloudResponse?.ram || application.hosting?.ram || 256,
      version: discloudResponse?.version || plan.version || null,
      main: discloudResponse?.main || null,
      status: "deploying",
      url: null,
      createdAt: application.hosting?.createdAt || now, // preserva data original se existir
      updatedAt: now,
      lastDeployAt: now,
    };

    application.hosting = newHosting;
    await application.save();

    // ── Auditoria ─────────────────────────────────────────────────────────────
    await auditService.log("application", "redeploy", adminId, id, {
      planId,
      planName: plan.name,
      botID,
      previousAppId: alreadyDeployed ? application.hosting?.appId : null,
      newAppId,
      ownerDiscordId,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
    });

    console.log(
      `[ADMIN REDEPLOY] Concluído — app: ${id}, novo appId Discloud: ${newAppId}`
    );

    return res.json({
      success: true,
      message: alreadyDeployed
        ? "Redeploy realizado com sucesso. O appId da Discloud foi atualizado."
        : "Deploy realizado com sucesso. A aplicação agora está hospedada na Discloud.",
      details: {
        applicationId: id,
        botID,
        newAppId,
        plan: plan.name,
        hosting: newHosting,
      },
    });
  } catch (error) {
    console.error("[ADMIN REDEPLOY] Erro inesperado:", error);
    return res.status(500).json({ error: "Erro interno ao fazer redeploy" });
  }
});

export default router;