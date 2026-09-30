// src/routes/admin/bot/requirements.js
// Rota para gerenciar o requirements.txt global dos bots
import { Router } from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";

const router = Router();

router.use(authMiddleware, requireAdmin);

const DEFAULT_REQUIREMENTS = `disnake
py-discord-html-transcripts
pymongo
dnspython
requests
pytz
aiohttp
websockets>=12.0
PyJWT>=2.8.0
matplotlib
psutil
PyNaCl
Pillow`;

/**
 * GET /api/admin/bot/requirements
 * Retorna o requirements.txt global atual
 */
router.get("/", async (req, res) => {
  try {
    const GlobalConfig = (await import("../../../database/models/GlobalConfig.js")).default;
    const config = await GlobalConfig.findOne({ key: "bot_requirements" }).lean();

    res.json({
      success: true,
      requirements: config?.value || DEFAULT_REQUIREMENTS,
      updatedAt: config?.updatedAt || null,
      updatedBy: config?.updatedBy || null,
    });
  } catch (error) {
    console.error("[ADMIN] Erro ao buscar requirements:", error);
    res.status(500).json({ error: "Erro ao buscar requirements" });
  }
});

/**
 * PUT /api/admin/bot/requirements
 * Atualiza o requirements.txt global
 * Body: { requirements: string, rebuild?: boolean }
 *
 * rebuild=false → só salva no banco (próximo deploy já pega o novo)
 * rebuild=true  → salva E faz commit em todos os bots ativos
 */
router.put("/", async (req, res) => {
  try {
    const { requirements, rebuild = false } = req.body;
    const adminId = String(req.user?._id || "");

    if (requirements === undefined || requirements === null) {
      return res.status(400).json({ error: "Campo 'requirements' é obrigatório" });
    }

    if (typeof requirements !== "string") {
      return res.status(400).json({ error: "requirements deve ser uma string" });
    }

    if (requirements.length > 10000) {
      return res.status(400).json({ error: "requirements não pode ultrapassar 10.000 caracteres" });
    }

    const GlobalConfig = (await import("../../../database/models/GlobalConfig.js")).default;

    const updated = await GlobalConfig.findOneAndUpdate(
      { key: "bot_requirements" },
      {
        key: "bot_requirements",
        value: requirements,
        updatedBy: adminId,
      },
      { upsert: true, new: true }
    );

    // Se não pediu rebuild, retorna aqui
    if (!rebuild) {
      return res.json({
        success: true,
        message: "requirements.txt atualizado com sucesso",
        requirements: updated.value,
        updatedAt: updated.updatedAt,
        rebuilt: false,
      });
    }

    // ── REBUILD: faz commit do requirements.txt em todos os bots ativos ──
    const Application = (await import("../../../database/models/Application.js")).default;

    // Busca todas as applications que têm appId na Discloud e não estão deletadas/bloqueadas
    const applications = await Application.find({
      "hosting.appId": { $exists: true, $ne: null, $ne: "" },
      isDeleted: false,
      isBlocked: false,
    }).lean();

    console.log(`[ADMIN REQUIREMENTS REBUILD] Iniciando rebuild em ${applications.length} bots`);

    // Dispara os commits de forma assíncrona (não bloqueia a resposta)
    res.json({
      success: true,
      message: `requirements.txt atualizado. Rebuild iniciado em ${applications.length} bot(s).`,
      requirements: updated.value,
      updatedAt: updated.updatedAt,
      rebuilt: true,
      totalBots: applications.length,
    });

    // Processa em background
    setImmediate(async () => {
      const { commitRequirementsToBot } = await import("../../../services/requirementsRebuildService.js");

      let success = 0;
      let failed = 0;

      for (const app of applications) {
        try {
          await commitRequirementsToBot(app.hosting.appId, requirements);
          success++;
          console.log(`[REQUIREMENTS REBUILD] ✅ ${app.hosting.appId} (${app.name}) atualizado`);
        } catch (err) {
          failed++;
          console.error(`[REQUIREMENTS REBUILD] ❌ ${app.hosting.appId} (${app.name}):`, err.message);
        }

        // Pequeno delay para não sobrecarregar a Discloud
        await new Promise((r) => setTimeout(r, 300));
      }

      console.log(`[REQUIREMENTS REBUILD] Concluído: ${success} sucesso, ${failed} falhas`);
    });
  } catch (error) {
    console.error("[ADMIN] Erro ao atualizar requirements:", error);
    res.status(500).json({ error: "Erro ao atualizar requirements" });
  }
});

export default router;