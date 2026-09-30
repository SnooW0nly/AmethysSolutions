import { Router } from "express";
import mongoose from "mongoose";
import Application from "../../../database/models/Application.js";
import User from "../../../database/models/User.js";
import BotConfig from "../../../database/models/BotConfig.js";
import discloudService from "../../../services/discloudService.js";
import auditService from "../../../services/auditService.js";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import redeployRoute from "./redeploy.js";

const router = Router();

// Middleware de autenticação e admin em todas as rotas
router.use(authMiddleware, requireAdmin);

/**
 * Valida se um ID é um ObjectId válido do MongoDB
 */
function validateObjectId(id, res) {
  if (!mongoose.Types.ObjectId.isValid(id)) {
    res.status(400).json({ error: "ID inválido" });
    return false;
  }
  return true;
}

/**
 * GET /api/admin/applications
 * Lista todas as aplicações com filtros
 */
router.get("/", async (req, res) => {
  try {
    const {
      page = 1,
      limit = 20,
      search = "",
      status = "",
      planId = "",
      userId = "",
      expired = "",
      blocked = "",
      sortBy = "createdAt",
      sortOrder = "desc",
    } = req.query;

    const query = { isDeleted: false };

    if (search) {
      if (/^\d+$/.test(search)) {
        const userByDiscord = await User.findOne({ discordId: search }).select("_id").lean();
        query.$or = [
          { "bot.owner": search },
          { "bot.id": search },
          { name: new RegExp(search, "i") },
          { "hosting.appId": new RegExp(search, "i") },
          { botID: new RegExp(search, "i") },
        ];
        if (userByDiscord) {
          query.$or.push({ userId: userByDiscord._id });
        }
      } else {
        query.$or = [
          { name: new RegExp(search, "i") },
          { "bot.id": new RegExp(search, "i") },
          { "bot.owner": new RegExp(search, "i") },
          { "hosting.appId": new RegExp(search, "i") },
          { botID: new RegExp(search, "i") },
          { "plan.name": new RegExp(search, "i") },
          { "plan.id": new RegExp(search, "i") },
        ];
      }
    }

    if (status) query["hosting.status"] = status;
    if (planId) query["plan.id"] = planId;
    if (userId) query.userId = userId;

    if (expired === "true") {
      query.expiresAt = { $lt: new Date() };
    } else if (expired === "false") {
      query.expiresAt = { $gte: new Date() };
    }

    if (blocked === "true") {
      query.isBlocked = true;
    } else if (blocked === "false") {
      query.isBlocked = false;
    }

    const skip = (page - 1) * limit;
    const sort = { [sortBy]: sortOrder === "asc" ? 1 : -1 };

    const [applications, total] = await Promise.all([
      Application.find(query)
        .populate("userId", "username email discordId avatar")
        .sort(sort)
        .skip(skip)
        .limit(parseInt(limit))
        .lean(),
      Application.countDocuments(query),
    ]);

    res.json({
      success: true,
      applications,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (error) {
    console.error("[ADMIN] Erro ao listar aplicações:", error);
    res.status(500).json({ error: "Erro ao listar aplicações" });
  }
});

/**
 * GET /api/admin/applications/:id
 */
router.get("/:id", async (req, res) => {
  try {
    const { id } = req.params;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ error: "ID inválido" });
    }

    const application = await Application.findById(id)
      .populate("userId", "username email discordId avatar")
      .populate("paymentId")
      .lean();

    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    let botConfig = null;
    if (application.botID) {
      botConfig = await BotConfig.findOne({ botID: application.botID }).lean();
    }

    let discloudInfo = null;
    let discloudStatus = null;
    if (application.hosting?.appId) {
      const [infoResult, statusResult] = await Promise.all([
        discloudService.getAppInfo(application.hosting.appId),
        discloudService.getAppStatus(application.hosting.appId),
      ]);
      if (infoResult.success) discloudInfo = infoResult.app;
      if (statusResult.success) discloudStatus = statusResult.status;
    }

    res.json({
      success: true,
      application,
      botConfig,
      discloudInfo,
      discloudStatus,
    });
  } catch (error) {
    console.error("[ADMIN] Erro ao buscar aplicação:", error);
    res.status(500).json({ error: "Erro ao buscar aplicação" });
  }
});

/**
 * PUT /api/admin/applications/:id
 */
router.put("/:id", async (req, res) => {
  try {
    const { id } = req.params;
    if (!validateObjectId(id, res)) return;

    const updates = req.body;
    const adminId = String(req.user?._id || "");

    const application = await Application.findById(id);
    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const allowedFields = [
      "name", "expiresAt", "isBlocked", "blockedAt", "canRecover",
      "plan", "hosting", "bot", "info", "botID",
    ];

    const updateData = {};
    for (const field of allowedFields) {
      if (updates[field] !== undefined) {
        updateData[field] = updates[field];
      }
    }

    if (updates.bot?.token && application.botID) {
      const targetOwner = updates.bot.owner || application.bot?.owner || "";
      const incomingPerms = Array.isArray(updates.bot.perms) ? updates.bot.perms : (Array.isArray(application.bot?.perms) ? application.bot.perms : []);
      const newPerms = Array.from(new Set([...(incomingPerms || []).filter(Boolean), ...(targetOwner ? [String(targetOwner)] : [])]));
      await BotConfig.findOneAndUpdate(
        { botID: application.botID },
        {
          "bot.token": updates.bot.token,
          "bot.owner": targetOwner,
          "bot.id": updates.bot.id || application.bot?.id,
          "bot.perms": newPerms,
          "bot.server": updates.bot.server || application.bot?.server,
        }
      );
    }

    Object.assign(application, updateData);
    await application.save();

    await auditService.log("application", "update", adminId, id, {
      updates: updateData,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
    });

    res.json({ success: true, message: "Aplicação atualizada com sucesso", application });
  } catch (error) {
    console.error("[ADMIN] Erro ao atualizar aplicação:", error);
    res.status(500).json({ error: "Erro ao atualizar aplicação" });
  }
});

/**
 * POST /api/admin/applications/:id/block
 */
router.post("/:id/block", async (req, res) => {
  try {
    const { id } = req.params;
    if (!validateObjectId(id, res)) return;

    const { reason } = req.body || {};
    const adminId = String(req.user?._id || "");

    const application = await Application.findById(id);
    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }
    if (application.isBlocked) {
      return res.status(400).json({ error: "Aplicação já está bloqueada" });
    }

    // Para na Discloud ao bloquear
    if (application.hosting?.appId) {
      const result = await discloudService.stopApp(application.hosting.appId);
      if (!result.success) {
        console.warn(`[ADMIN BLOCK] Não foi possível parar app ${application.hosting.appId} na Discloud: ${result.error}`);
      } else {
        console.log(`[ADMIN BLOCK] App ${application.hosting.appId} parado na Discloud`);
      }
    }

    application.isBlocked = true;
    application.blockedAt = new Date();
    await application.save();

    await auditService.log("application", "block", adminId, id, {
      reason,
      appId: application.hosting?.appId,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
    });

    res.json({ success: true, message: "Aplicação bloqueada com sucesso" });
  } catch (error) {
    console.error("[ADMIN] Erro ao bloquear aplicação:", error);
    res.status(500).json({ error: "Erro ao bloquear aplicação" });
  }
});

/**
 * POST /api/admin/applications/:id/unblock
 */
router.post("/:id/unblock", async (req, res) => {
  try {
    const { id } = req.params;
    if (!validateObjectId(id, res)) return;

    const adminId = String(req.user?._id || "");

    const application = await Application.findById(id);
    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }
    if (!application.isBlocked) {
      return res.status(400).json({ error: "Aplicação não está bloqueada" });
    }

    // Inicia na Discloud ao desbloquear
    if (application.hosting?.appId) {
      const result = await discloudService.startApp(application.hosting.appId);
      if (!result.success) {
        console.warn(`[ADMIN UNBLOCK] Não foi possível iniciar app ${application.hosting.appId} na Discloud: ${result.error}`);
      } else {
        console.log(`[ADMIN UNBLOCK] App ${application.hosting.appId} iniciado na Discloud`);
      }
    }

    application.isBlocked = false;
    application.blockedAt = null;
    await application.save();

    await auditService.log("application", "unblock", adminId, id, {
      appId: application.hosting?.appId,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
    });

    res.json({ success: true, message: "Aplicação desbloqueada com sucesso" });
  } catch (error) {
    console.error("[ADMIN] Erro ao desbloquear aplicação:", error);
    res.status(500).json({ error: "Erro ao desbloquear aplicação" });
  }
});

/**
 * DELETE /api/admin/applications/:id
 *
 * Query params:
 * - deleteFrom: "database" | "discloud" | "both"
 * - permanent: true/false (para database)
 */
router.delete("/:id", async (req, res) => {
  try {
    const { id } = req.params;
    if (!validateObjectId(id, res)) return;

    const {
      deleteFrom = "database",
      permanent = false,
    } = req.query;

    const adminId = String(req.user?._id || "");

    const application = await Application.findById(id);
    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const normalizedDeleteFrom = deleteFrom;

    let discloudDeleted = false;
    let databaseDeleted = false;

    const appId = application.hosting?.appId;

    // ─── Deleta da Discloud ────────────────────────────────────────────────────
    const shouldDeleteFromDiscloud =
      normalizedDeleteFrom === "discloud" ||
      normalizedDeleteFrom === "both" ||
      normalizedDeleteFrom === "database";

    if (shouldDeleteFromDiscloud && appId) {
      const deleteResult = await discloudService.deleteApp(appId);
      if (deleteResult.success) {
        discloudDeleted = true;
        console.log(`[ADMIN DELETE] App ${appId} deletado da Discloud`);
        application.hosting = {
          ...application.hosting,
          appId: null,
          status: "deleted",
        };
      } else {
        console.error(`[ADMIN DELETE] Falha ao deletar app ${appId} da Discloud: ${deleteResult.error}`);
        if (normalizedDeleteFrom === "discloud") {
          return res.status(500).json({
            error: `Erro ao deletar da Discloud: ${deleteResult.error}`,
          });
        }
        console.warn(`[ADMIN DELETE] Continuando deleção do banco mesmo com falha na Discloud`);
      }
      await application.save();
    } else if (shouldDeleteFromDiscloud && !appId) {
      console.log(`[ADMIN DELETE] App ${id} não tem appId na Discloud — pulando deleção na Discloud`);
    }

    // ─── Deleta do banco ─────────────────────────────────────────────────────
    if (normalizedDeleteFrom === "database" || normalizedDeleteFrom === "both") {
      if (permanent === "true" || permanent === true) {
        await Application.deleteOne({ _id: id });

        if (application.botID) {
          await BotConfig.deleteOne({ botID: application.botID });
          console.log(`[ADMIN DELETE] BotConfig ${application.botID} removido`);
        }
        databaseDeleted = true;
        console.log(`[ADMIN DELETE] Aplicação ${id} removida permanentemente do banco`);
      } else {
        application.isDeleted = true;
        application.deletedAt = new Date();
        await application.save();
        databaseDeleted = true;
        console.log(`[ADMIN DELETE] Aplicação ${id} marcada como deletada (soft delete)`);
      }
    }

    // ─── Auditoria ───────────────────────────────────────────────────────────
    await auditService.log(
      "application",
      `delete_${normalizedDeleteFrom}${permanent === "true" || permanent === true ? "_permanent" : ""}`,
      adminId,
      id,
      {
        appId,
        botID: application.botID,
        deleteFrom: normalizedDeleteFrom,
        permanent,
        discloudDeleted,
        databaseDeleted,
        ip: req.ip,
        userAgent: req.headers["user-agent"],
      }
    );

    const summaryParts = [];
    if (discloudDeleted) summaryParts.push("Discloud");
    if (databaseDeleted) summaryParts.push(permanent === "true" || permanent === true ? "Database (permanente)" : "Database (soft delete)");
    if (summaryParts.length === 0) summaryParts.push("Nenhuma ação realizada");

    res.json({
      success: true,
      message: `Aplicação deletada: ${summaryParts.join(" e ")}`,
      details: {
        discloudDeleted,
        databaseDeleted,
        permanent: normalizedDeleteFrom !== "discloud" ? permanent : null,
      },
    });
  } catch (error) {
    console.error("[ADMIN] Erro ao deletar aplicação:", error);
    res.status(500).json({ error: "Erro ao deletar aplicação" });
  }
});

/**
 * POST /api/admin/applications/:id/restore
 */
router.post("/:id/restore", async (req, res) => {
  try {
    const { id } = req.params;
    if (!validateObjectId(id, res)) return;

    const adminId = String(req.user?._id || "");

    const application = await Application.findById(id);
    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }
    if (!application.isDeleted) {
      return res.status(400).json({ error: "Aplicação não está deletada" });
    }
    if (!application.canRecover) {
      return res.status(400).json({ error: "Aplicação não pode ser recuperada" });
    }

    application.isDeleted = false;
    application.deletedAt = null;
    await application.save();

    await auditService.log("application", "restore", adminId, id, {
      ip: req.ip,
      userAgent: req.headers["user-agent"],
    });

    res.json({ success: true, message: "Aplicação restaurada com sucesso" });
  } catch (error) {
    console.error("[ADMIN] Erro ao restaurar aplicação:", error);
    res.status(500).json({ error: "Erro ao restaurar aplicação" });
  }
});

/**
 * POST /api/admin/applications/:id/restart
 */
router.post("/:id/restart", async (req, res) => {
  try {
    const { id } = req.params;
    if (!validateObjectId(id, res)) return;

    const adminId = String(req.user?._id || "");

    const application = await Application.findById(id);
    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }
    if (!application.hosting?.appId) {
      return res.status(400).json({ error: "Aplicação não tem ID na Discloud" });
    }

    const result = await discloudService.restartApp(application.hosting.appId);
    if (!result.success) {
      return res.status(500).json({ error: result.error });
    }

    await auditService.log("application", "restart", adminId, id, {
      appId: application.hosting.appId,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
    });

    res.json({ success: true, message: result.message });
  } catch (error) {
    console.error("[ADMIN] Erro ao reiniciar aplicação:", error);
    res.status(500).json({ error: "Erro ao reiniciar aplicação" });
  }
});

/**
 * POST /api/admin/applications/:id/stop
 */
router.post("/:id/stop", async (req, res) => {
  try {
    const { id } = req.params;
    if (!validateObjectId(id, res)) return;

    const adminId = String(req.user?._id || "");

    const application = await Application.findById(id);
    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }
    if (!application.hosting?.appId) {
      return res.status(400).json({ error: "Aplicação não tem ID na Discloud" });
    }

    const result = await discloudService.stopApp(application.hosting.appId);
    if (!result.success) {
      return res.status(500).json({ error: result.error });
    }

    await auditService.log("application", "stop", adminId, id, {
      appId: application.hosting.appId,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
    });

    res.json({ success: true, message: result.message });
  } catch (error) {
    console.error("[ADMIN] Erro ao parar aplicação:", error);
    res.status(500).json({ error: "Erro ao parar aplicação" });
  }
});

/**
 * POST /api/admin/applications/:id/start
 */
router.post("/:id/start", async (req, res) => {
  try {
    const { id } = req.params;
    if (!validateObjectId(id, res)) return;

    const adminId = req.user?.id || req.user?.discordId;

    const application = await Application.findById(id);
    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }
    if (!application.hosting?.appId) {
      return res.status(400).json({ error: "Aplicação não tem ID na Discloud" });
    }

    const result = await discloudService.startApp(application.hosting.appId);
    if (!result.success) {
      return res.status(500).json({ error: result.error });
    }

    await auditService.log("application", "start", adminId, id, {
      appId: application.hosting.appId,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
    });

    res.json({ success: true, message: result.message });
  } catch (error) {
    console.error("[ADMIN] Erro ao iniciar aplicação:", error);
    res.status(500).json({ error: "Erro ao iniciar aplicação" });
  }
});

/**
 * GET /api/admin/applications/:id/logs
 */
router.get("/:id/logs", async (req, res) => {
  try {
    const { id } = req.params;
    if (!validateObjectId(id, res)) return;

    const application = await Application.findById(id);
    if (!application) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }
    if (!application.hosting?.appId) {
      return res.status(400).json({ error: "Aplicação não tem ID na Discloud" });
    }

    const result = await discloudService.getAppLogs(application.hosting.appId);
    if (!result.success) {
      return res.status(500).json({ error: result.error });
    }

    res.json({ success: true, logs: result.logs });
  } catch (error) {
    console.error("[ADMIN] Erro ao buscar logs:", error);
    res.status(500).json({ error: "Erro ao buscar logs" });
  }
});

router.use("/", redeployRoute);

export default router;
