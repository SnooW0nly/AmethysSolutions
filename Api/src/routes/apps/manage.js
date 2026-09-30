import express from "express";
import Application from "../../database/models/Application.js";
import discloudService from "../../services/discloudService.js";
import discloudCache from "../../services/discloud/cache.js";

const router = express.Router();

async function performAction(action, appId) {
  let result;
  switch (action) {
    case "start":
      result = await discloudService.startApp(appId);
      break;
    case "stop":
      result = await discloudService.stopApp(appId);
      break;
    case "restart":
    case "rebuild": // Discloud não tem 'rebuild' direto, usamos restart ou commit. Aqui usamos restart.
      result = await discloudService.restartApp(appId);
      break;
    default:
      throw new Error("Ação inválida");
  }

  if (!result.success) {
    throw new Error(result.error || `Erro ao executar ${action}`);
  }

  return result;
}

async function handleManage(req, res, action) {
  try {
    const userId = req.user?._id;
    const { id } = req.params;

    const app = await Application.findOne({ _id: id, userId })
      .select({ hosting: { appId: 1, provider: 1 }, "bot.token": 1, "bot.server": 1, isBlocked: 1, isDeleted: 1, expiresAt: 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    if (app.isBlocked && (action === "start" || action === "restart" || action === "rebuild")) {
      return res.status(403).json({
        error: "Aplicação bloqueada por vencimento",
        errorCode: "APP_BLOCKED",
        message: "Sua aplicação foi bloqueada por vencimento. Renove para desbloquear.",
        expiresAt: app.expiresAt,
      });
    }

    if (app.isDeleted) {
      return res.status(403).json({
        error: "Aplicação deletada",
        errorCode: "APP_DELETED",
        message: "Sua aplicação foi deletada. Entre em contato com o suporte.",
      });
    }

    const appId = app?.hosting?.appId;
    if (!appId) {
      return res.status(400).json({ error: "Aplicação sem provider/appId vinculado" });
    }

    if (app?.hosting?.provider !== "discloud") {
      return res.status(400).json({ error: "Aplicação ainda não migrada para a Discloud. Entre em contato com o suporte." });
    }

    const botConfigured = Boolean(app?.bot?.token || "");
    if ((action === "start" || action === "restart" || action === "rebuild") && !botConfigured) {
      return res.status(400).json({ error: "Bot não configurado", errorCode: "BOT_NOT_CONFIGURED" });
    }

    const serverConfigured = Boolean(app?.bot?.server || "");
    if ((action === "start" || action === "restart" || action === "rebuild") && !serverConfigured) {
      return res.status(400).json({ error: "Servidor não configurado", errorCode: "SERVER_NOT_CONFIGURED" });
    }

    const result = await performAction(action, appId);

    if (action === "start" || action === "restart" || action === "rebuild") {
      await Application.findByIdAndUpdate(id, {
        $set: {
          lastStartedAt: new Date(),
          inactivityWarningSentAt: null,
        },
      });
    }

    if (action === "restart" || action === "rebuild") {
      discloudCache.markAsRestarting(appId);
    }

    return res.json({ ok: true, message: result.message || "Operação realizada com sucesso" });
  } catch (e) {
    return res.status(400).json({ error: e.message || `Falha ao ${action} aplicação` });
  }
}

router.post("/:id/start",   (req, res) => handleManage(req, res, "start"));
router.post("/:id/stop",    (req, res) => handleManage(req, res, "stop"));
router.post("/:id/restart", (req, res) => handleManage(req, res, "restart"));
router.post("/:id/rebuild", (req, res) => handleManage(req, res, "rebuild"));

export default router;